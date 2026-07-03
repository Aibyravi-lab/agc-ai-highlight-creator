import uuid
from pathlib import Path

from app.config.config import settings


class JobStorageService:

    SUBFOLDERS = (
        "frames",
        "clips",
        "thumbnails",
        "reels",
        "captions",
        "audio",
        "results",
    )

    @classmethod
    def initialize(cls) -> None:

        Path(settings.JOBS_FOLDER).mkdir(
            parents=True,
            exist_ok=True
        )

    @classmethod
    def resolve_job_id(
        cls,
        job_id: str | None
    ) -> str:

        return job_id or uuid.uuid4().hex

    @classmethod
    def job_dir(
        cls,
        job_id: str
    ) -> Path:

        return (
            Path(settings.JOBS_FOLDER)
            / job_id
        )

    @classmethod
    def subfolder(
        cls,
        job_id: str,
        name: str
    ) -> Path:

        folder = (
            cls.job_dir(job_id)
            / name
        )

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        return folder
