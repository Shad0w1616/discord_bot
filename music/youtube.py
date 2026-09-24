# from __future__ import annotations

# import asyncio
# from typing import Any

# import yt_dlp

# from music.models import Track, Playlist
# from settings import settings
# from utils.logger import logger



# class YoutubeService:
#     """
#     Работа с YouTube через yt-dlp.

#     Отвечает только за:
#     - получение информации о видео;
#     - получение информации о плейлистах;
#     - получение прямого audio stream URL.

#     Воспроизведением занимается MusicPlayer.
#     """



#     def __init__(
#         self
#     ):

#         self.options = {

#             "format": "bestaudio/best",

#             "quiet": True,

#             "no_warnings": True,

#             "skip_download": True,

#             "noplaylist": False,

#             "ignoreerrors": True,

#             "default_search": "ytsearch",

#         }



#         if settings.YTDLP_COOKIES_PATH:

#             self.options[
#                 "quiet": True,
#                 "cookiefile": settings.COOKIE_FILE,
#             ] = settings.YTDLP_COOKIES_PATH





#     # =====================================================
#     # Общий extractor
#     # =====================================================


#     async def extract(
#         self,
#         query: str
#     ) -> dict[str, Any] | None:
#         """
#         Запуск yt-dlp в отдельном потоке,
#         чтобы не блокировать Discord event loop.
#         """

#         loop = asyncio.get_running_loop()


#         return await loop.run_in_executor(

#             None,

#             lambda: self._extract_sync(query)

#         )





#     def _extract_sync(
#         self,
#         query: str
#     ) -> dict[str, Any] | None:


#         try:

#             with yt_dlp.YoutubeDL(
#                 self.options
#             ) as ydl:


#                 return ydl.extract_info(

#                     query,

#                     download=False

#                 )


#         except Exception as error:


#             logger.error(

#                 f"yt-dlp error: {error}"

#             )


#             return None





#     # =====================================================
#     # Один трек
#     # =====================================================


#     async def get_track(
#         self,
#         query: str,
#         guild_id: int,
#         requester=None
#     ) -> Track:
#         """
#         Получить один трек.
#         """

#         info = await self.extract(
#             query
#         )


#         if not info:

#             raise RuntimeError(
#                 "Видео не найдено"
#             )



#         # Если ytsearch вернул список

#         if info.get(
#             "entries"
#         ):


#             info = next(

#                 (
#                     item

#                     for item in info["entries"]

#                     if item

#                 ),

#                 None

#             )



#         if not info:

#             raise RuntimeError(
#                 "Видео недоступно"
#             )



#         webpage_url = (

#             info.get(
#                 "webpage_url"
#             )

#             or info.get(
#                 "original_url"
#             )

#         )



#         if not webpage_url:

#             raise RuntimeError(
#                 "Не удалось получить URL видео"
#             )



#         track = Track(

#             title=info.get(

#                 "title",

#                 "Unknown"

#             ),

#             url=webpage_url,

#             guild_id=guild_id,

#             duration=info.get(
#                 "duration"
#             ),

#             thumbnail=info.get(
#                 "thumbnail"
#             )

#         )



#         if requester:

#             track.set_requester(
#                 requester
#             )



#         return track





#     # =====================================================
#     # Плейлист
#     # =====================================================


#     async def get_playlist(
#         self,
#         query: str,
#         guild_id: int,
#         requester=None
#     ) -> Playlist:
#         """
#         Получение YouTube плейлиста.
#         """

#         info = await self.extract(
#             query
#         )


#         if not info:

#             raise RuntimeError(
#                 "Плейлист недоступен"
#             )



#         playlist = Playlist(

#             title=info.get(

#                 "title",

#                 "YouTube playlist"

#             )

#         )



#         entries = info.get(
#             "entries"
#         )



#         if not entries:

#             return playlist





#         for item in entries:


#             if (

#                 playlist.count

#                 >=

#                 settings.MAX_PLAYLIST_SIZE

#             ):

#                 break



#             if not item:

#                 continue



#             url = (

#                 item.get(
#                     "webpage_url"
#                 )

#                 or item.get(
#                     "original_url"
#                 )

#             )



#             if not url:

#                 continue



#             track = Track(

#                 title=item.get(

#                     "title",

#                     "Unknown"

#                 ),

#                 url=url,

#                 guild_id=guild_id,

#                 duration=item.get(
#                     "duration"
#                 ),

#                 thumbnail=item.get(
#                     "thumbnail"
#                 )

#             )



#             if requester:

#                 track.set_requester(
#                     requester
#                 )



#             playlist.add_track(
#                 track
#             )



#         return playlist





#     # =====================================================
#     # Audio stream
#     # =====================================================


#     async def get_stream_url(
#         self,
#         url: str
#     ) -> str:
#         """
#         Получение временного audio URL
#         для FFmpeg.
#         """

#         loop = asyncio.get_running_loop()



#         return await loop.run_in_executor(

#             None,

#             lambda: self._stream_sync(url)

#         )





#     def _stream_sync(
#         self,
#         url: str
#     ) -> str:
#         """
#         Получение прямого audio stream URL
#         для FFmpeg.
#         """

#         options = self.options.copy()


#         options.update({

#             "format":
#                 "bestaudio/best",

#             "noplaylist":
#                 True

#         })


#         with yt_dlp.YoutubeDL(
#             options
#         ) as ydl:


#             info = ydl.extract_info(

#                 url,

#                 download=False

#             )


#             if not info:

#                 raise RuntimeError(
#                     "YouTube info отсутствует"
#                 )



#             # Иногда yt-dlp возвращает вложенный результат

#             if info.get("entries"):


#                 info = next(

#                     (
#                         item

#                         for item in info["entries"]

#                         if item

#                     ),

#                     None

#                 )



#             if not info:

#                 raise RuntimeError(
#                     "Видео не найдено"
#                 )



#             # Старый вариант

#             if info.get("url"):

#                 return info["url"]



#             # Новый вариант через formats

#             formats = info.get(
#                 "formats",
#                 []
#             )


#             audio_formats = [

#                 f

#                 for f in formats

#                 if (

#                     f.get("acodec")

#                     and

#                     f.get("acodec") != "none"

#                 )

#             ]



#             if not audio_formats:

#                 raise RuntimeError(
#                     "Audio formats отсутствуют"
#                 )



#             # Берём лучший audio формат

#             best_audio = max(

#                 audio_formats,

#                 key=lambda x: (

#                     x.get(
#                         "abr"
#                     )

#                     or 0

#                 )

#             )


#             stream_url = best_audio.get(
#                 "url"
#             )



#             if not stream_url:

#                 raise RuntimeError(
#                     "Audio URL отсутствует"
#                 )



#             return stream_url
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yt_dlp

from music.models import Track, Playlist
from settings import settings
from utils.logger import logger

_EXTRACTION_SEMAPHORE = asyncio.Semaphore(
    settings.MAX_CONCURRENT_EXTRACTIONS
)


class YoutubeService:
    """
    Работа с YouTube через yt-dlp.

    Отвечает только за:
    - получение информации о видео;
    - получение информации о плейлистах;
    - получение прямого audio stream URL.

    Воспроизведением занимается MusicPlayer.
    """

    def __init__(self):

        self.options = {

            "format":
                "bestaudio[ext=m4a]/bestaudio/best",

            "quiet":
                True,

            "no_warnings":
                True,

            "skip_download":
                True,

            "noplaylist":
                False,

            "playlistend":
                settings.MAX_PLAYLIST_SIZE,

            "extract_flat":
                "in_playlist",

            "ignoreerrors":
                False,

            "default_search":
                "ytsearch",

            "cachedir":
                str(
                    settings.YTDLP_CACHE_DIR
                ),

            "extractor_args": {

                "youtube": {

                    "player_client": [
                        "android",
                        "web"
                    ]

                }

            }

        }


        self._setup_cookies()



    # =====================================================
    # Cookies
    # =====================================================

    def _setup_cookies(self):
        """
        Добавление cookies для yt-dlp.
        """

        if not settings.YTDLP_COOKIES_PATH:
            return


        cookie_path = Path(
            settings.YTDLP_COOKIES_PATH
        )


        if cookie_path.exists():

            self.options["cookiefile"] = str(
                cookie_path
            )

            logger.info(
                "yt-dlp cookies loaded"
            )

        else:

            logger.warning(
                f"Cookies file not found: {cookie_path}"
            )



    # =====================================================
    # Общий extractor
    # =====================================================

    async def extract(
        self,
        query: str,
        playlist_limit: int | None = None
    ) -> dict[str, Any] | None:

        loop = asyncio.get_running_loop()


        async with _EXTRACTION_SEMAPHORE:
            return await loop.run_in_executor(
                None,
                lambda: self._extract_sync(
                    f"ytsearch1:{query}"
                    if not query.startswith("http")
                    else query,
                    playlist_limit
                )
            )



    def _extract_sync(
        self,
        query: str,
        playlist_limit: int | None = None
    ) -> dict[str, Any] | None:

        try:

            options = self.options.copy()
            if playlist_limit is not None:
                options["playlistend"] = max(1, playlist_limit)
            with yt_dlp.YoutubeDL(options) as ydl:

                return ydl.extract_info(
                    query,
                    download=False
                )


        except Exception as error:

            logger.exception(
                f"yt-dlp extract error: {error}"
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

        info = await self.extract(
            query
        )


        if not info:

            raise RuntimeError(
                "Видео не найдено"
            )


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
                "URL видео отсутствует"
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
        requester=None,
        max_items: int | None = None
    ) -> Playlist:

        info = await self.extract(
            query,
            playlist_limit=max_items
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


            limit = min(
                settings.MAX_PLAYLIST_SIZE,
                max_items if max_items is not None else settings.MAX_PLAYLIST_SIZE
            )

            if playlist.count >= limit:

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


        loop = asyncio.get_running_loop()


        async with _EXTRACTION_SEMAPHORE:
            return await loop.run_in_executor(
                None,
                lambda: self._stream_sync(url)
            )



    def _stream_sync(
        self,
        url: str
    ) -> str:


        options = self.options.copy()


        options.update({

            "format":
                "bestaudio/best",

            "noplaylist":
                True

        })


        try:

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:


                info = ydl.extract_info(

                    url,

                    download=False

                )


        except Exception as error:

            logger.exception(
                f"yt-dlp stream error: {error}"
            )

            raise



        if not info:

            raise RuntimeError(
                "YouTube info отсутствует"
            )


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


        if info.get("url"):

            return info["url"]



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
