import os
import threading
from datetime import datetime, timedelta

from app.config.config import settings


class UploadCacheService:

    _cache: dict = {}
    _lock = threading.Lock()

    @classmethod
    def _key(
        cls,
        user_id: int,
        filename: str,
        size: int
    ) -> tuple:
        return (user_id, filename.lower(), size)

    @classmethod
    def get_duplicate(
        cls,
        user_id: int,
        filename: str,
        size: int
    ) -> dict | None:

        key = cls._key(user_id, filename, size)
        window = timedelta(
            minutes=settings.DUPLICATE_UPLOAD_WINDOW_MINUTES
        )

        with cls._lock:

            entry = cls._cache.get(key)

            if entry is None:
                return None

            stored_at, upload_info = entry

            if datetime.utcnow() - stored_at > window:
                del cls._cache[key]
                return None

            location = upload_info.get("location")

            if not location or not os.path.isfile(location):
                cls._cache.pop(key, None)
                return None

            return upload_info

    @classmethod
    def store(
        cls,
        user_id: int,
        filename: str,
        size: int,
        upload_info: dict
    ) -> None:

        key = cls._key(user_id, filename, size)

        with cls._lock:
            cls._cache[key] = (datetime.utcnow(), upload_info)

    @classmethod
    def evict_expired(cls) -> None:

        window = timedelta(
            minutes=settings.DUPLICATE_UPLOAD_WINDOW_MINUTES
        )
        cutoff = datetime.utcnow() - window

        with cls._lock:

            expired = [
                k for k, (ts, _) in cls._cache.items()
                if ts < cutoff
            ]

            for k in expired:
                del cls._cache[k]
