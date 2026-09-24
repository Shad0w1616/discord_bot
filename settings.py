# from __future__ import annotations

# import os
# import shutil
# from pathlib import Path

# from dotenv import load_dotenv


# load_dotenv()

# COOKIE_FILE = "/app/cookies.txt"

# class Settings:
#     """
#     Все настройки приложения.

#     Источник данных:
#     - переменные окружения;
#     - .env файл для локальной разработки.

#     В Docker значения должны приходить
#     через environment.
#     """



#     # =====================================================
#     # Discord
#     # =====================================================


#     DISCORD_TOKEN: str = os.getenv(
#         "DISCORD_TOKEN",
#         ""
#     )


#     COMMAND_PREFIX: str = os.getenv(
#         "COMMAND_PREFIX",
#         "!"
#     )



#     # =====================================================
#     # FFmpeg
#     # =====================================================


#     FFMPEG_PATH: str = os.getenv(
#         "FFMPEG_PATH",
#         "ffmpeg"
#     )



#     @property
#     def ffmpeg_available(
#         self
#     ) -> bool:
#         """
#         Проверка наличия ffmpeg.

#         В Linux Docker:
#         обычно ожидается /usr/bin/ffmpeg
#         или просто ffmpeg.
#         """

#         return shutil.which(
#             self.FFMPEG_PATH
#         ) is not None





#     # =====================================================
#     # YouTube / yt-dlp
#     # =====================================================


#     YTDLP_COOKIES_PATH: str | None = os.getenv(
#         "YTDLP_COOKIES_PATH"
#     )


#     YTDLP_CACHE_DIR: Path = Path(
#         os.getenv(
#             "YTDLP_CACHE_DIR",
#             "/tmp/yt-dlp"
#         )
#     )



#     @property
#     def cookies_available(
#         self
#     ) -> bool:

#         if not self.YTDLP_COOKIES_PATH:

#             return False


#         return Path(
#             self.YTDLP_COOKIES_PATH
#         ).exists()





#     # =====================================================
#     # Queue
#     # =====================================================


#     MAX_PLAYLIST_SIZE: int = int(

#         os.getenv(
#             "MAX_PLAYLIST_SIZE",
#             "100"
#         )

#     )



#     # =====================================================
#     # Voice
#     # =====================================================


#     DISCONNECT_TIMEOUT: int = int(

#         os.getenv(
#             "DISCONNECT_TIMEOUT",
#             "300"
#         )

#     )



#     # =====================================================
#     # Logging
#     # =====================================================


#     LOG_LEVEL: str = os.getenv(

#         "LOG_LEVEL",

#         "INFO"

#     )





# settings = Settings()
from __future__ import annotations

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class Settings:
    """
    Все настройки приложения.

    Источник данных:
    - переменные окружения;
    - .env файл для локальной разработки.

    В Docker значения должны приходить
    через environment.
    """



    # =====================================================
    # Discord
    # =====================================================


    DISCORD_TOKEN: str = os.getenv(
        "DISCORD_TOKEN",
        ""
    )


    COMMAND_PREFIX: str = os.getenv(
        "COMMAND_PREFIX",
        "!"
    )





    FFMPEG_PATH: str = os.getenv(
        "FFMPEG_PATH",
        "ffmpeg"
    )



    @property
    def ffmpeg_available(
        self
    ) -> bool:
        """
        Проверка наличия ffmpeg.
        """

        return shutil.which(
            self.FFMPEG_PATH
        ) is not None





    # =====================================================
    # YouTube / yt-dlp
    # =====================================================


    YTDLP_COOKIES_PATH: str | None = os.getenv(
        "YTDLP_COOKIES_PATH",
        "/app/cookies.txt"
    )


    YTDLP_CACHE_DIR: Path = Path(
        os.getenv(
            "YTDLP_CACHE_DIR",
            "/tmp/yt-dlp"
        )
    )



    @property
    def cookies_available(
        self
    ) -> bool:
        """
        Проверка наличия cookies файла.
        """

        if not self.YTDLP_COOKIES_PATH:

            return False


        return Path(
            self.YTDLP_COOKIES_PATH
        ).exists()




    # =====================================================
    # Queue
    # =====================================================


    MAX_PLAYLIST_SIZE: int = int(

        os.getenv(
            "MAX_PLAYLIST_SIZE",
            "100"
        )

    )

    MAX_QUEUE_SIZE: int = int(
        os.getenv("MAX_QUEUE_SIZE", "200")
    )

    PLAY_COOLDOWN_SECONDS: float = float(
        os.getenv("PLAY_COOLDOWN_SECONDS", "5")
    )

    MAX_CONCURRENT_EXTRACTIONS: int = int(
        os.getenv("MAX_CONCURRENT_EXTRACTIONS", "2")
    )

    QUEUE_STATE_PATH: Path = Path(
        os.getenv("QUEUE_STATE_PATH", "data/queues.json")
    )

    DAILY_VICTIMS_STATE_PATH: Path = Path(
        os.getenv("DAILY_VICTIMS_STATE_PATH", "data/daily_victims.json")
    )





    # =====================================================
    # Voice
    # =====================================================


    DISCONNECT_TIMEOUT: int = int(

        os.getenv(
            "DISCONNECT_TIMEOUT",
            "300"
        )

    )





    # =====================================================
    # Logging
    # =====================================================


    LOG_LEVEL: str = os.getenv(

        "LOG_LEVEL",

        "INFO"

    )





settings = Settings()
