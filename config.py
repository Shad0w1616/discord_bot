from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:

    #########################
    # Discord
    #########################

    DISCORD_TOKEN: str = os.getenv(
        "DISCORD_TOKEN",
        ""
    )

    COMMAND_PREFIX: str = "!"

    #########################
    # FFmpeg
    #########################

    FFMPEG_PATH: str = os.getenv(
        "FFMPEG_PATH",
        "ffmpeg"
    )

    FFMPEG_OPTIONS: dict = None

    #########################
    # yt-dlp
    #########################

    YTDLP_OPTIONS: dict = None

    #########################
    # Queue
    #########################

    AUTO_DISCONNECT_TIMEOUT: int = 30

    MAX_QUEUE_PREVIEW: int = 5

    #########################
    # Logging
    #########################

    LOG_LEVEL: str = "INFO"

    LOG_DIRECTORY: str = "logs"

    def __post_init__(self):

        self.FFMPEG_OPTIONS = {

            "before_options":
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 5",

            "options":
                "-vn"
        }

        self.YTDLP_OPTIONS = {

            "format":
                "bestaudio/best",

            "quiet":
                True,

            "no_warnings":
                True,

            "skip_download":
                True,

            "noplaylist":
                False
        }


settings = Settings()