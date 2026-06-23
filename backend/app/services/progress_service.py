import json
from pathlib import Path


class ProgressService:

    PROGRESS_FILE = Path(
        "storage/progress.json"
    )

    @classmethod
    def update(
        cls,
        progress: int,
        status: str
    ):

        cls.PROGRESS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            cls.PROGRESS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "progress": progress,
                    "status": status
                },
                file,
                indent=4
            )

    @classmethod
    def get_progress(
        cls
    ):

        if not cls.PROGRESS_FILE.exists():

            return {
                "progress": 0,
                "status": ""
            }

        with open(
            cls.PROGRESS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(
                file
            )