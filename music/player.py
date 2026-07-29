from __future__ import annotations

import asyncio
from typing import Optional, Callable, Awaitable

import discord

from music.models import Track
from music.queue import MusicQueue
from music.youtube import YoutubeService

from settings import settings
from utils.logger import logger



class MusicPlayer:
    """
    Музыкальный проигрыватель одного Discord guild.

    Один экземпляр:
    один сервер → один voice connection → один player.
    """



    def __init__(
        self,
        voice_client: discord.VoiceClient,
        text_channel: discord.TextChannel,
        loop: asyncio.AbstractEventLoop
    ):

        self.voice_client = voice_client

        self.text_channel = text_channel

        self.loop = loop

        self.queue = MusicQueue()

        self.youtube = YoutubeService()


        self.current: Optional[Track] = None


        self.disconnect_task: Optional[
            asyncio.Task
        ] = None


        self.play_lock = asyncio.Lock()


        self.on_track_start: Optional[
            Callable[[Track], Awaitable]
        ] = None



    # =====================================================
    # Добавление треков
    # =====================================================


    async def enqueue(
        self,
        track: Track
    ) -> None:


        self.queue.add(
            track
        )


        self.cancel_disconnect_timer()



        if self.current is None:

            asyncio.create_task(
                self.play_next()
            )





    async def enqueue_many(
        self,
        tracks: list[Track]
    ) -> None:


        self.queue.add_many(
            tracks
        )


        self.cancel_disconnect_timer()



        if self.current is None:

            asyncio.create_task(
                self.play_next()
            )





    # =====================================================
    # Воспроизведение
    # =====================================================


    async def play_next(
        self
    ) -> None:


        async with self.play_lock:


            if self.voice_client.is_playing():

                return



            track = self.queue.get_next()



            if track is None:


                self.current = None


                await self.start_disconnect_timer()


                return



            self.current = track



            try:


                stream_url = await self.youtube.get_stream_url(

                    track.url

                )



                source = discord.FFmpegPCMAudio(

                    stream_url,

                    executable=settings.FFMPEG_PATH,

                    before_options=(

                        "-reconnect 1 "

                        "-reconnect_streamed 1 "

                        "-reconnect_delay_max 5"

                    ),

                    options="-vn"

                )



                self.voice_client.play(

                    source,

                    after=self.after_track

                )



                if self.on_track_start:


                    await self.on_track_start(
                        track
                    )



            except Exception:

                logger.exception(
                    "Ошибка запуска трека"
                )

                self.current = None

                await self.start_disconnect_timer()

                return





    # =====================================================
    # Завершение трека
    # =====================================================


    def after_track(
        self,
        error
    ):


        if error:

            logger.error(

                f"Voice playback error: {error}"

            )



        asyncio.run_coroutine_threadsafe(

            self.track_finished(),

            self.loop

        )





    async def track_finished(
        self
    ):


        self.current = None


        asyncio.create_task(
            self.play_next()
        )





    # =====================================================
    # Управление
    # =====================================================


    def toggle_pause(
        self
    ) -> bool:


        if self.voice_client.is_paused():


            self.voice_client.resume()

            return False



        if self.voice_client.is_playing():


            self.voice_client.pause()

            return True



        return False





    async def skip(
        self
    ) -> bool:


        if not (

            self.voice_client.is_playing()

            or self.voice_client.is_paused()

        ):

            return False



        self.voice_client.stop()


        return True





    # =====================================================
    # Очередь
    # =====================================================


    def get_queue_preview(
        self,
        limit: int = 5
    ) -> list[Track]:


        return self.queue.preview(
            limit
        )





    # =====================================================
    # Автовыход
    # =====================================================


    async def start_disconnect_timer(
        self
    ):


        self.cancel_disconnect_timer()



        self.disconnect_task = asyncio.create_task(

            self.disconnect_after_timeout()

        )





    async def disconnect_after_timeout(
        self
    ):


        try:


            await asyncio.sleep(

                settings.DISCONNECT_TIMEOUT

            )



            if (

                self.current is None

                and self.queue.empty()

                and not self.voice_client.is_playing()

            ):


                await self.voice_client.disconnect()



        except asyncio.CancelledError:


            return





    def cancel_disconnect_timer(
        self
    ):


        if self.disconnect_task:


            self.disconnect_task.cancel()

            self.disconnect_task = None





    # =====================================================
    # Завершение
    # =====================================================


    async def shutdown(
        self
    ):


        self.cancel_disconnect_timer()



        self.queue.clear()



        self.current = None



        if (

            self.voice_client.is_playing()

            or self.voice_client.is_paused()

        ):

            self.voice_client.stop()



        if self.voice_client.is_connected():


            await self.voice_client.disconnect()    