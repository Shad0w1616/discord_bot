from __future__ import annotations

import logging
import sys

from settings import settings



def setup_logger() -> logging.Logger:
    """
    Настройка логирования.

    В Docker контейнере логи должны идти
    в stdout/stderr, чтобы Docker engine
    мог их собирать.
    """



    logger = logging.getLogger(
        "notorious"
    )



    if logger.handlers:

        return logger



    level = getattr(

        logging,

        settings.LOG_LEVEL.upper(),

        logging.INFO

    )



    logger.setLevel(
        level
    )



    handler = logging.StreamHandler(
        sys.stdout
    )



    formatter = logging.Formatter(

        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"

    )



    handler.setFormatter(
        formatter
    )


    logger.addHandler(
        handler
    )


    logger.propagate = False



    return logger





logger = setup_logger()