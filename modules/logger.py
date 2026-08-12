from __future__ import annotations

import logging
import os
import sys

import config


class ANSIColorFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLOR_CODES.get(record.levelno, self.RESET)
        record.levelname_color = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(level=logging.INFO, log_file=None):
    if log_file is None:
        log_file = getattr(
            config, "LOG_FILE_PATH", os.path.join(config.DEBUG_DIR, "bot_activity.log")
        )

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ANSIColorFormatter(
        "[%(asctime)s] [%(levelname_color)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name="BombCryptoBot"):
    return logging.getLogger(name)


logger = get_logger("BombCryptoBot")
