from __future__ import annotations

import asyncio
from typing import Any

import yt_dlp

from music.models import Track, Playlist
from settings import settings
from utils.logger import logger



class YoutubeService:
    """
    Работа с YouTube через yt-dlp.

    Отвечает только за:
    - получение информации о видео;
    - получение информации о плейлистах;
    - получение прямого audio stream URL.

    Воспроизведением занимается MusicPlayer.
    """



    def __init__(
        self
    ):

        self.options = {

            "format": "bestaudio/best",

            "quiet": True,

            "no_warnings": True,

            "skip_download": True,

            "noplaylist": False,

            "ignoreerrors": True,

            "default_search": "ytsearch",

        }



        if settings.YTDLP_COOKIES_PATH:

            self.options[
                "cookiefile"
            ] = settings.YTDLP_COOKIES_PATH





    # =====================================================
    # Общий extractor
    # =====================================================


    async def extract(
        self,
        query: str
    ) -> dict[str, Any] | None:
        """
        Запуск yt-dlp в отдельном потоке,
        чтобы не блокировать Discord event loop.
        """

        loop = asyncio.get_running_loop()


        return await loop.run_in_executor(

            None,

            lambda: self._extract_sync(query)

        )





    def _extract_sync(
        self,
        query: str
    ) -> dict[str, Any] | None:


        try:

            with yt_dlp.YoutubeDL(
                self.options
            ) as ydl:


                return ydl.extract_info(

                    query,

                    download=False

                )


        except Exception as error:


            logger.error(

                f"yt-dlp error: {error}"

            )


            return None





    # =====================================================
    # Один трек
    # =====================================================


    async def get_track(
        self,
        query: str,
        guild_id: int,
        requester=None
    ) -> Track:
        """
        Получить один трек.
        """

        info = await self.extract(
            query
        )


        if not info:

            raise RuntimeError(
                "Видео не найдено"
            )



        # Если ytsearch вернул список

        if info.get(
            "entries"
        ):


            info = next(

                (
                    item

                    for item in info["entries"]

                    if item

                ),

                None

            )



        if not info:

            raise RuntimeError(
                "Видео недоступно"
            )



        webpage_url = (

            info.get(
                "webpage_url"
            )

            or info.get(
                "original_url"
            )

        )



        if not webpage_url:

            raise RuntimeError(
                "Не удалось получить URL видео"
            )



        track = Track(

            title=info.get(

                "title",

                "Unknown"

            ),

            url=webpage_url,

            guild_id=guild_id,

            duration=info.get(
                "duration"
            ),

            thumbnail=info.get(
                "thumbnail"
            )

        )



        if requester:

            track.set_requester(
                requester
            )



        return track





    # =====================================================
    # Плейлист
    # =====================================================


    async def get_playlist(
        self,
        query: str,
        guild_id: int,
        requester=None
    ) -> Playlist:
        """
        Получение YouTube плейлиста.
        """

        info = await self.extract(
            query
        )


        if not info:

            raise RuntimeError(
                "Плейлист недоступен"
            )



        playlist = Playlist(

            title=info.get(

                "title",

                "YouTube playlist"

            )

        )



        entries = info.get(
            "entries"
        )



        if not entries:

            return playlist





        for item in entries:


            if (

                playlist.count

                >=

                settings.MAX_PLAYLIST_SIZE

            ):

                break



            if not item:

                continue



            url = (

                item.get(
                    "webpage_url"
                )

                or item.get(
                    "original_url"
                )

            )



            if not url:

                continue



            track = Track(

                title=item.get(

                    "title",

                    "Unknown"

                ),

                url=url,

                guild_id=guild_id,

                duration=item.get(
                    "duration"
                ),

                thumbnail=item.get(
                    "thumbnail"
                )

            )



            if requester:

                track.set_requester(
                    requester
                )



            playlist.add_track(
                track
            )



        return playlist





    # =====================================================
    # Audio stream
    # =====================================================


    async def get_stream_url(
        self,
        url: str
    ) -> str:
        """
        Получение временного audio URL
        для FFmpeg.
        """

        loop = asyncio.get_running_loop()



        return await loop.run_in_executor(

            None,

            lambda: self._stream_sync(url)

        )





    def _stream_sync(
        self,
        url: str
    ) -> str:
        """
        Получение прямого audio stream URL
        для FFmpeg.
        """

        options = self.options.copy()


        options.update({

            "format":
                "bestaudio/best",

            "noplaylist":
                True

        })


        with yt_dlp.YoutubeDL(
            options
        ) as ydl:


            info = ydl.extract_info(

                url,

                download=False

            )


            if not info:

                raise RuntimeError(
                    "YouTube info отсутствует"
                )



            # Иногда yt-dlp возвращает вложенный результат

            if info.get("entries"):


                info = next(

                    (
                        item

                        for item in info["entries"]

                        if item

                    ),

                    None

                )



            if not info:

                raise RuntimeError(
                    "Видео не найдено"
                )



            # Старый вариант

            if info.get("url"):

                return info["url"]



            # Новый вариант через formats

            formats = info.get(
                "formats",
                []
            )


            audio_formats = [

                f

                for f in formats

                if (

                    f.get("acodec")

                    and

                    f.get("acodec") != "none"

                )

            ]



            if not audio_formats:

                raise RuntimeError(
                    "Audio formats отсутствуют"
                )



            # Берём лучший audio формат

            best_audio = max(

                audio_formats,

                key=lambda x: (

                    x.get(
                        "abr"
                    )

                    or 0

                )

            )


            stream_url = best_audio.get(
                "url"
            )



            if not stream_url:

                raise RuntimeError(
                    "Audio URL отсутствует"
                )



            return stream_url