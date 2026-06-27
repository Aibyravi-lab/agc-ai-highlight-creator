import json
from pathlib import Path
from datetime import datetime

from app.config.config import settings


class HistoryService:

    HISTORY_FILE = Path(
        settings.HISTORY_FILE
    )

    @classmethod
    def add_history(
        cls,
        video_name: str,
        reel_path: str,
        highlights_count: int
    ):

        cls.HISTORY_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        history = []

        if cls.HISTORY_FILE.exists():

            with open(
                cls.HISTORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                try:
                    history = json.load(file)
                except Exception:
                    history = []

        history.append({

            "video_name":
            video_name,

            "date":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "reel_path":
            reel_path,

            "highlights_count":
            highlights_count

        })

        with open(
            cls.HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                indent=4
            )

    @classmethod
    def get_history(cls):

        if not cls.HISTORY_FILE.exists():
            return []

        with open(
            cls.HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)