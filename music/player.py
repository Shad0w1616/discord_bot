from __future__ import annotations

import asyncio
from collections import deque
from typing import Optional

import discord

from music.models import Track
from music.queue import MusicQueue
from music.storage import QueueStorage
from music.youtube import YoutubeService
from music.wave import WaveSession
from music.controls import PlayerControls
from settings import settings
from utils.embeds import error_embed, now_playing_embed
from utils.logger import logger


class MusicPlayer:
    """Музыкальный проигрыватель одного Discord-сервера."""

    def __init__(
        self,
        voice_client: discord.VoiceClient,
        text_channel: discord.TextChannel,
        loop: asyncio.AbstractEventLoop,
        storage: QueueStorage,
    ) -> None:
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.loop = loop
        self.guild_id = voice_client.guild.id
        self.storage = storage
        self.queue = MusicQueue()
        self.youtube = YoutubeService()
        self.current: Optional[Track] = None
        self.repeat_enabled = False
        self._skip_requested = False
        self._shutting_down = False
        self.disconnect_task: Optional[asyncio.Task] = None
        self.play_lock = asyncio.Lock()
        self.wave: WaveSession | None = None
        self._wave_loading = False
        self._epoch = 0
        self.history: deque[Track] = deque(maxlen=100)
        self.panel_view: PlayerControls | None = None
        self.panel_message: discord.Message | None = None
        self._panel_lock = asyncio.Lock()

    def panel_embed(self) -> discord.Embed:
        embed = now_playing_embed(self.current)
        state = "Пауза" if self.voice_client.is_paused() else "Сейчас играет"
        embed.title = state
        mode = f"Волна • доиграно {self.wave.completed}/{self.wave.limit}" if self.wave else "Обычная очередь"
        embed.set_footer(text=f"{mode} • Повтор: {'вкл' if self.repeat_enabled else 'выкл'}")
        return embed

    async def close_panel(self) -> None:
        async with self._panel_lock:
            view, message = self.panel_view, self.panel_message
            self.panel_view = self.panel_message = None
            if view is None:
                return
            view.active = False
            for item in view.children:
                item.disabled = True
            view.stop()
            if message is not None:
                try:
                    await message.edit(view=view)
                except discord.HTTPException:
                    logger.warning("Не удалось отключить старую панель")

    async def show_panel(self) -> None:
        await self.close_panel()
        async with self._panel_lock:
            if self.current is None or self._shutting_down:
                return
            view = PlayerControls(self)
            self.panel_view = view
            try:
                self.panel_message = await self.text_channel.send(embed=self.panel_embed(), view=view)
            except discord.HTTPException:
                view.active = False
                view.stop()
                self.panel_view = None
                logger.warning("Не удалось отправить панель текущего трека")

    async def refresh_panel(self) -> None:
        async with self._panel_lock:
            if self.panel_view is None or self.panel_message is None or self.current is None:
                return
            self.panel_view.sync_buttons()
            try:
                await self.panel_message.edit(embed=self.panel_embed(), view=self.panel_view)
            except discord.HTTPException:
                logger.warning("Не удалось обновить панель текущего трека")

    @property
    def wave_active(self) -> bool:
        return self.wave is not None or self._wave_loading

    def require_normal_mode(self) -> None:
        if self.wave_active:
            raise RuntimeError("Сначала остановите волну командой /wave_stop.")
        if self._shutting_down:
            raise RuntimeError("Плеер отключается. Подключитесь заново.")

    async def start_wave(self, query: str, count: int, requester=None) -> Track:
        self.require_normal_mode()
        if self.current or not self.queue.empty():
            raise RuntimeError("Сначала завершите обычную очередь или используйте /stop.")
        if not 1 <= count <= 200:
            raise RuntimeError("Укажите от 1 до 200 треков.")
        query = query.strip()
        if not query:
            raise RuntimeError("Введите название песни или ссылку YouTube.")
        if query.startswith(("http://", "https://")):
            query = f"https://www.youtube.com/watch?v={self.youtube.video_id(query)}"
        self._wave_loading = True
        self.cancel_disconnect_timer()
        epoch = self._epoch
        try:
            seed = await self.youtube.get_track(query, self.guild_id, requester)
            if epoch != self._epoch or self._shutting_down:
                raise RuntimeError("Запуск волны отменён.")
            seed.url = f"https://www.youtube.com/watch?v={self.youtube.video_id(seed.url)}"
            wave = WaveSession(seed, count)
            wave.add([seed])
            if count > 1:
                wave.queried.add(seed.url)
                wave.add(await self.youtube.get_mix(seed))
                if len(wave.pending) < 2:
                    raise RuntimeError("YouTube не вернул рекомендации для этого трека.")
            if epoch != self._epoch or self._shutting_down:
                raise RuntimeError("Запуск волны отменён.")
            self.wave = wave
            self.history.clear()
            self.repeat_enabled = False
            asyncio.create_task(self.play_next())
            return seed
        finally:
            if epoch == self._epoch:
                self._wave_loading = False
                if self.wave is None:
                    await self.start_disconnect_timer()

    async def stop_wave(self) -> bool:
        if not self.wave_active:
            return False
        self._epoch += 1
        self._wave_loading = False
        self.wave = None
        self.current = None
        self._skip_requested = False
        self.repeat_enabled = False
        self.history.clear()
        self.voice_client.stop()
        await self.close_panel()
        await self.start_disconnect_timer()
        return True

    async def _notify(self, message: str) -> None:
        try:
            await self.text_channel.send(message)
        except discord.HTTPException:
            logger.warning("Не удалось отправить сообщение плеера")

    async def restore(self) -> int:
        tracks = await self.storage.load(self.guild_id)
        if tracks:
            self.queue.add_many(tracks[:settings.MAX_QUEUE_SIZE])
        return self.queue.size()

    async def enqueue(self, track: Track) -> None:
        self.require_normal_mode()
        if self.queue.size() >= settings.MAX_QUEUE_SIZE:
            raise RuntimeError(f"Очередь заполнена: максимум {settings.MAX_QUEUE_SIZE} треков.")
        self.queue.add(track)
        await self._persist()
        self.cancel_disconnect_timer()
        if self.current is None:
            asyncio.create_task(self.play_next())
        await self.refresh_panel()

    async def enqueue_many(self, tracks: list[Track]) -> int:
        self.require_normal_mode()
        available = settings.MAX_QUEUE_SIZE - self.queue.size()
        accepted = tracks[:max(0, available)]
        if not accepted:
            raise RuntimeError(f"Очередь заполнена: максимум {settings.MAX_QUEUE_SIZE} треков.")
        self.queue.add_many(accepted)
        await self._persist()
        self.cancel_disconnect_timer()
        if self.current is None:
            asyncio.create_task(self.play_next())
        await self.refresh_panel()
        return len(accepted)

    async def play_next(self) -> None:
        async with self.play_lock:
            if (self._shutting_down or self._wave_loading or self.current is not None
                    or not self.voice_client.is_connected()
                    or self.voice_client.is_playing() or self.voice_client.is_paused()):
                return

            epoch = self._epoch
            wave = self.wave
            if wave:
                try:
                    track = await wave.next_track(self.youtube)
                except Exception:
                    logger.exception("Ошибка получения продолжения YouTube Mix")
                    track = None
                if epoch != self._epoch:
                    return
                if track is None:
                    self.wave = None
                    self.repeat_enabled = False
                    self.history.clear()
                    await self._notify(
                        f"Волна завершена: {wave.completed}/{wave.limit} треков."
                        + (" YouTube не предоставил новых доступных рекомендаций."
                           if wave.completed < wave.limit else "")
                    )
            else:
                track = self.queue.get_next()
            if track is None:
                self.current = None
                await self._persist()
                await self.start_disconnect_timer()
                return

            self.current = track
            await self._persist()
            source = None
            try:
                stream_url = await self.youtube.get_stream_url(track.url)
                if epoch != self._epoch or self._shutting_down:
                    return
                source = discord.FFmpegPCMAudio(
                    stream_url,
                    executable=settings.FFMPEG_PATH,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    options="-vn",
                )
                self.voice_client.play(source, after=lambda error: self.after_track(error, epoch))
            except Exception:
                if source is not None:
                    source.cleanup()
                if epoch != self._epoch:
                    return
                logger.exception("Ошибка запуска трека: %s", track.title)
                self.current = None
                if wave:
                    wave.failures += 1
                    if wave.failures >= 10:
                        self.wave = None
                        self.repeat_enabled = False
                        self.history.clear()
                        await self._notify("Волна остановлена после 10 ошибок подряд. Проверьте доступ к YouTube.")
                await self._persist()
                try:
                    await self.text_channel.send(
                        embed=error_embed(f"Не удалось запустить **{track.title}**. Перехожу к следующему треку.")
                    )
                except discord.HTTPException:
                    logger.warning("Не удалось отправить сообщение об ошибке воспроизведения")
                asyncio.create_task(self.play_next())
                return

            await self.show_panel()

    def after_track(self, error, epoch=None) -> None:
        if error:
            logger.error("Voice playback error: %s", error)
        if not self._shutting_down:
            asyncio.run_coroutine_threadsafe(self.track_finished(error, epoch), self.loop)

    async def track_finished(self, error=None, epoch=None) -> None:
        async with self.play_lock:
            if self._shutting_down or (epoch is not None and epoch != self._epoch):
                return
            finished = self.current
            self.current = None
            repeat = bool(finished and self.repeat_enabled and not self._skip_requested and not error)
            if self.wave and finished:
                if error:
                    self.wave.failures += 1
                    if self.wave.failures >= 10:
                        self.wave = None
                        self.repeat_enabled = False
                        self.history.clear()
                        await self._notify("Волна остановлена после 10 ошибок воспроизведения подряд.")
                elif not self._skip_requested:
                    if finished.url not in self.wave.completed_urls:
                        self.wave.completed_urls.add(finished.url)
                        self.wave.completed += 1
                    self.wave.failures = 0
                if repeat and self.wave and self.wave.completed < self.wave.limit:
                    self.wave.pending.appendleft(finished)
            elif repeat:
                self.queue.add_first(finished)
            if finished and not error and not repeat:
                self.history.append(finished)
            self._skip_requested = False
            await self._persist()
            await self.close_panel()
        asyncio.create_task(self.play_next())

    async def previous(self) -> None:
        async with self.play_lock:
            if (self.current is None or self._shutting_down
                    or not (self.voice_client.is_playing() or self.voice_client.is_paused())):
                raise RuntimeError("Дождитесь начала воспроизведения.")
            if not self.history:
                raise RuntimeError("Предыдущего трека пока нет.")
            if not self.wave and self.queue.size() + 2 > settings.MAX_QUEUE_SIZE:
                raise RuntimeError("Для возврата освободите два места в очереди.")
            previous = self.history.pop()
            current = self.current
            self._epoch += 1
            self.current = None
            self._skip_requested = False
            self.voice_client.stop()
            if self.wave:
                self.wave.pending.appendleft(current)
                self.wave.pending.appendleft(previous)
            else:
                self.queue.add_first(current)
                self.queue.add_first(previous)
            await self._persist()
            await self.close_panel()
        asyncio.create_task(self.play_next())

    def toggle_pause(self) -> bool | None:
        if self.voice_client.is_paused():
            self.voice_client.resume()
            return False
        if self.voice_client.is_playing():
            self.voice_client.pause()
            return True
        return None

    async def skip(self) -> bool:
        if not (self.voice_client.is_playing() or self.voice_client.is_paused()):
            return False
        self._skip_requested = True
        self.voice_client.stop()
        return True

    async def remove(self, position: int) -> Track:
        self.require_normal_mode()
        track = self.queue.remove(position)
        await self._persist()
        await self.refresh_panel()
        return track

    async def shuffle(self) -> int:
        self.require_normal_mode()
        self.queue.shuffle()
        await self._persist()
        await self.refresh_panel()
        return self.queue.size()

    async def clear_queue(self) -> None:
        self.require_normal_mode()
        self.queue.clear()
        await self._persist()
        await self.refresh_panel()

    async def set_repeat(self, enabled: bool) -> None:
        if self._shutting_down:
            raise RuntimeError("Плеер отключается.")
        self.repeat_enabled = enabled
        await self.refresh_panel()

    async def start_disconnect_timer(self) -> None:
        self.cancel_disconnect_timer()
        self.disconnect_task = asyncio.create_task(self.disconnect_after_timeout())

    async def disconnect_after_timeout(self) -> None:
        try:
            await asyncio.sleep(settings.DISCONNECT_TIMEOUT)
            if self.current is None and self.queue.empty() and not self.voice_client.is_playing():
                await self.voice_client.disconnect()
        except asyncio.CancelledError:
            pass

    def cancel_disconnect_timer(self) -> None:
        if self.disconnect_task:
            self.disconnect_task.cancel()
            self.disconnect_task = None

    async def shutdown(self, preserve_queue: bool = False) -> None:
        self._shutting_down = True
        self._epoch += 1
        if self.wave_active:
            self.wave = None
            self._wave_loading = False
            self.current = None
        self.cancel_disconnect_timer()
        if preserve_queue:
            await self._persist()
        else:
            self.queue.clear()
            self.current = None
            await self._persist()
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
        if self.voice_client.is_connected():
            await self.voice_client.disconnect()
        await self.close_panel()

    async def _persist(self) -> None:
        if self.wave_active:
            return
        tracks = self.queue.all()
        if self.current is not None:
            tracks.insert(0, self.current)
        await self.storage.save(self.guild_id, tracks)
