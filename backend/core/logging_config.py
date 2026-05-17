from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import LOG_DIR, ensure_directories


def configure_logging() -> None:
    ensure_directories()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        LOG_DIR / "study_lock.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    crash_handler = RotatingFileHandler(
        LOG_DIR / "crash.log",
        maxBytes=500_000,
        backupCount=3,
        encoding="utf-8",
    )
    crash_handler.setLevel(logging.ERROR)
    crash_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(crash_handler)
    root_logger.addHandler(console_handler)
