from __future__ import annotations

import asyncio
import re
from typing import Optional

import yt_dlp

from config import settings

from music.models import (
    Track,
    Playlist
)

from music.exceptions import (
    InvalidYoutubeUrlError,
    TrackNotFoundError,
    YoutubeSearchError,
    AudioStreamError
)


class YoutubeService:
    """
    Сервис работы с YouTube.

    Отвечает только за:

    - поиск видео;
    - получение информации о видео;
    - получение плейлистов;
    - получение аудиопотоков.

    Не занимается:

    - очередью;
    - Discord;
    - воспроизведением.
    """


    YOUTUBE_REGEX = re.compile(
        r"^(https?://)?"
        r"(www\.)?"
        r"(youtube\.com|youtu\.be)/.+$"
    )


    def __init__(self):

        self.options = (
            settings.YTDLP_OPTIONS.copy()
        )


    # =====================================================
    # Проверка URL
    # =====================================================

    def is_youtube_url(
        self,
        value: str
    ) -> bool:
        """
        Проверяет является ли строка
        YouTube-ссылкой.
        """

        return bool(
            self.YOUTUBE_REGEX.match(
                value
            )
        )


    # =====================================================
    # Выполнение yt-dlp в отдельном потоке
    # =====================================================

    async def _extract_info(
        self,
        query: str
    ) -> dict:
        """
        Асинхронная обёртка над yt-dlp.

        yt-dlp синхронный,
        поэтому запускаем через executor.
        """

        loop = asyncio.get_running_loop()


        try:

            result = await loop.run_in_executor(

                None,

                self._extract_sync,

                query

            )

            return result


        except Exception as error:

            raise YoutubeSearchError(
                str(error)
            )


    def _extract_sync(
        self,
        query: str
    ) -> dict:
        """
        Синхронный вызов yt-dlp.
        """


        with yt_dlp.YoutubeDL(
            self.options
        ) as ydl:

            return ydl.extract_info(
                query,
                download=False
            )


    # =====================================================
    # Поиск одного трека
    # =====================================================

    async def search(
        self,
        query: str
    ) -> Track:
        """
        Поиск первого результата
        на YouTube.

        Пример:

        "Eminem Lose Yourself"

        превращается в:

        ytsearch1:Eminem Lose Yourself
        """


        if not self.is_youtube_url(
            query
        ):

            query = (
                f"ytsearch1:{query}"
            )


        info = await self._extract_info(
            query
        )


        # Результат поиска
        if "entries" in info:

            entries = info.get(
                "entries"
            )


            if not entries:

                raise TrackNotFoundError(
                    "Трек не найден."
                )


            info = entries[0]


        return self._convert_track(
            info
        )


    # =====================================================
    # Получение видео по URL
    # =====================================================

    async def get_track(
        self,
        url: str
    ) -> Track:
        """
        Получает информацию
        об одном видео.
        """


        if not self.is_youtube_url(
            url
        ):

            raise InvalidYoutubeUrlError(
                "Это не ссылка YouTube."
            )


        info = await self._extract_info(
            url
        )


        return self._convert_track(
            info
        )


    # =====================================================
    # Получение плейлиста
    # =====================================================

    async def get_playlist(
        self,
        url: str
    ) -> Playlist:
        """
        Получает YouTube-плейлист.
        """


        if not self.is_youtube_url(
            url
        ):

            raise InvalidYoutubeUrlError(
                "Плейлист должен быть ссылкой YouTube."
            )


        info = await self._extract_info(
            url
        )


        entries = info.get(
            "entries"
        )


        if not entries:

            raise TrackNotFoundError(
                "Плейлист пуст."
            )


        tracks = []


        for entry in entries:

            if not entry:

                continue


            try:

                track = (
                    self._convert_track(
                        entry
                    )
                )


                tracks.append(
                    track
                )


            except Exception:

                continue


        if not tracks:

            raise TrackNotFoundError(
                "В плейлисте нет доступных треков."
            )


        return Playlist(

            title=info.get(
                "title",
                "YouTube Playlist"
            ),

            uploader=info.get(
                "uploader"
            ),

            webpage_url=info.get(
                "webpage_url"
            ),

            thumbnail=info.get(
                "thumbnail"
            ),

            tracks=tracks
        )


    # =====================================================
    # Универсальный обработчик
    # =====================================================

    async def resolve(
        self,
        query: str
    ) -> Track | Playlist:
        """
        Определяет что передал пользователь:

        - поиск;
        - видео;
        - плейлист.
        """


        # Поисковый запрос
        if not self.is_youtube_url(
            query
        ):

            return await self.search(
                query
            )


        info = await self._extract_info(
            query
        )


        if info.get(
            "_type"
        ) == "playlist":

            return await self.get_playlist(
                query
            )


        return self._convert_track(
            info
        )


    # =====================================================
    # Получение прямого аудиопотока
    # =====================================================

    async def get_stream_url(
        self,
        track: Track
    ) -> str:
        """
        Получает временную ссылку
        аудиопотока для FFmpeg.
        """


        loop = asyncio.get_running_loop()


        try:

            url = await loop.run_in_executor(

                None,

                self._get_stream_sync,

                track.webpage_url

            )


            return url


        except Exception as error:

            raise AudioStreamError(
                str(error)
            )


    def _get_stream_sync(
        self,
        url: str
    ) -> str:
        """
        Синхронное получение stream URL.
        """


        options = {

            "format":
                "bestaudio/best",

            "quiet":
                True,

            "no_warnings":
                True,

            "noplaylist":
                True

        }


        with yt_dlp.YoutubeDL(
            options
        ) as ydl:


            info = ydl.extract_info(
                url,

                download=False
            )


            stream = info.get(
                "url"
            )


            if not stream:

                raise AudioStreamError(
                    "Аудиопоток отсутствует."
                )


            return stream


    # =====================================================
    # Конвертация yt-dlp -> Track
    # =====================================================

    def _convert_track(
        self,
        info: dict
    ) -> Track:
        """
        Превращает ответ yt-dlp
        в наш объект Track.
        """


        video_url = (
            info.get(
                "webpage_url"
            )
        )


        if not video_url:

            video_id = info.get(
                "id"
            )


            if video_id:

                video_url = (
                    "https://youtube.com/watch?v="
                    f"{video_id}"
                )


        if not video_url:

            raise TrackNotFoundError(
                "Не удалось получить URL видео."
            )


        return Track(

            title=info.get(
                "title",
                "Unknown"
            ),

            webpage_url=video_url,

            duration=info.get(
                "duration"
            ),

            uploader=info.get(
                "uploader"
            ),

            thumbnail=info.get(
                "thumbnail"
            )

        )