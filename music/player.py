from __future__ import annotations

import asyncio
from typing import Optional

import discord

from music.models import Track
from music.queue import MusicQueue
from music.storage import QueueStorage
from music.youtube import YoutubeService
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

    async def restore(self) -> int:
        tracks = await self.storage.load(self.guild_id)
        if tracks:
            self.queue.add_many(tracks[:settings.MAX_QUEUE_SIZE])
        return self.queue.size()

    async def enqueue(self, track: Track) -> None:
        if self.queue.size() >= settings.MAX_QUEUE_SIZE:
            raise RuntimeError(f"Очередь заполнена: максимум {settings.MAX_QUEUE_SIZE} треков.")
        self.queue.add(track)
        await self._persist()
        self.cancel_disconnect_timer()
        if self.current is None:
            asyncio.create_task(self.play_next())

    async def enqueue_many(self, tracks: list[Track]) -> int:
        available = settings.MAX_QUEUE_SIZE - self.queue.size()
        accepted = tracks[:max(0, available)]
        if not accepted:
            raise RuntimeError(f"Очередь заполнена: максимум {settings.MAX_QUEUE_SIZE} треков.")
        self.queue.add_many(accepted)
        await self._persist()
        self.cancel_disconnect_timer()
        if self.current is None:
            asyncio.create_task(self.play_next())
        return len(accepted)

    async def play_next(self) -> None:
        async with self.play_lock:
            if self.voice_client.is_playing() or self.voice_client.is_paused():
                return

            track = self.queue.get_next()
            if track is None:
                self.current = None
                await self._persist()
                await self.start_disconnect_timer()
                return

            self.current = track
            await self._persist()
            try:
                stream_url = await self.youtube.get_stream_url(track.url)
                source = discord.FFmpegPCMAudio(
                    stream_url,
                    executable=settings.FFMPEG_PATH,
                    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    options="-vn",
                )
                self.voice_client.play(source, after=self.after_track)
            except Exception:
                logger.exception("Ошибка запуска трека: %s", track.title)
                self.current = None
                await self._persist()
                try:
                    await self.text_channel.send(
                        embed=error_embed(f"Не удалось запустить **{track.title}**. Перехожу к следующему треку.")
                    )
                except discord.HTTPException:
                    logger.warning("Не удалось отправить сообщение об ошибке воспроизведения")
                asyncio.create_task(self.play_next())
                return

            try:
                await self.text_channel.send(embed=now_playing_embed(track))
            except discord.HTTPException:
                logger.warning("Не удалось отправить сообщение о текущем треке")

    def after_track(self, error) -> None:
        if error:
            logger.error("Voice playback error: %s", error)
        if not self._shutting_down:
            asyncio.run_coroutine_threadsafe(self.track_finished(), self.loop)

    async def track_finished(self) -> None:
        finished = self.current
        self.current = None
        if finished and self.repeat_enabled and not self._skip_requested:
            self.queue.add_first(finished)
        self._skip_requested = False
        await self._persist()
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
        track = self.queue.remove(position)
        await self._persist()
        return track

    async def shuffle(self) -> int:
        self.queue.shuffle()
        await self._persist()
        return self.queue.size()

    async def clear_queue(self) -> None:
        self.queue.clear()
        await self._persist()

    async def set_repeat(self, enabled: bool) -> None:
        self.repeat_enabled = enabled

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

    async def _persist(self) -> None:
        tracks = self.queue.all()
        if self.current is not None:
            tracks.insert(0, self.current)
        await self.storage.save(self.guild_id, tracks)
