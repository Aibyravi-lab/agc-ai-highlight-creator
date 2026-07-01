import json
import logging
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        data: dict = {
            "timestamp": self.formatTime(
                record,
                "%Y-%m-%dT%H:%M:%S"
            ),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id") and record.request_id:
            data["request_id"] = record.request_id

        if hasattr(record, "user_id") and record.user_id is not None:
            data["user_id"] = record.user_id

        if hasattr(record, "job_id") and record.job_id:
            data["job_id"] = record.job_id

        return json.dumps(data)


class LoggerService:

    LOG_DIR = Path("logs")

    LOG_FILE = LOG_DIR / "agc.log"

    _logger = logging.getLogger("agc")

    @classmethod
    def initialize(cls):

        cls.LOG_DIR.mkdir(
            exist_ok=True
        )

        cls._logger.setLevel(logging.INFO)

        if not cls._logger.handlers:
            handler = logging.FileHandler(
                str(cls.LOG_FILE)
            )
            handler.setFormatter(StructuredFormatter())
            cls._logger.addHandler(handler)

        cls._logger.propagate = False

        cls._logger.info(
            "AGC Logger Initialized"
        )

    @classmethod
    def info(
        cls,
        message: str,
        *,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> None:

        cls._logger.info(
            message,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "job_id": job_id,
            }
        )

    @classmethod
    def error(
        cls,
        message: str,
        *,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> None:

        cls._logger.error(
            message,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "job_id": job_id,
            }
        )
