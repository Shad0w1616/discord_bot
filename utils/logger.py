import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings


LOGGER_NAME = "notorious_bot"


def setup_logger() -> logging.Logger:
    """
    Создает и настраивает логгер проекта.

    Логи пишутся одновременно:
        • в консоль
        • в файл logs/bot.log
    """

    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers:
        return logger

    logger.setLevel(settings.LOG_LEVEL)

    log_directory = Path(settings.LOG_DIRECTORY)
    log_directory.mkdir(
        exist_ok=True
    )

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | "
            "%(levelname)-8s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%d.%m.%Y %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        formatter
    )

    file_handler = RotatingFileHandler(
        log_directory / "bot.log",
        encoding="utf-8",
        maxBytes=5 * 1024 * 1024,
        backupCount=5
    )

    file_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        console_handler
    )

    logger.addHandler(
        file_handler
    )

    logger.propagate = False

    return logger


logger = setup_logger()