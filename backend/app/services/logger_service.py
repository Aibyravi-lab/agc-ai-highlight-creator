import logging
from pathlib import Path


class LoggerService:

    LOG_DIR = Path("logs")

    LOG_FILE = LOG_DIR / "agc.log"

    @classmethod
    def initialize(cls):

        cls.LOG_DIR.mkdir(
            exist_ok=True
        )

        logging.basicConfig(
            filename=str(cls.LOG_FILE),
            level=logging.INFO,
            format=(
                "%(asctime)s | "
                "%(levelname)s | "
                "%(message)s"
            )
        )

        logging.info(
            "AGC Logger Initialized"
        )

    @staticmethod
    def info(message):

        logging.info(message)

    @staticmethod
    def error(message):

        logging.error(message)