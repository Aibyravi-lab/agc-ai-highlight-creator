import json

from app.services.job_storage_service import JobStorageService


class ProgressService:

    @classmethod
    def _progress_file(
        cls,
        job_id: str | None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_dir = (
            JobStorageService.subfolder(
                resolved_job_id,
                "results"
            )
        )

        return output_dir / "progress.json"

    @classmethod
    def update(
        cls,
        progress: int,
        status: str,
        job_id: str | None = None
    ):

        progress_file = cls._progress_file(job_id)

        with open(
            progress_file,
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
        cls,
        job_id: str | None = None
    ):

        progress_file = cls._progress_file(job_id)

        if not progress_file.exists():

            return {
                "progress": 0,
                "status": ""
            }

        with open(
            progress_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)