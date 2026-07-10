from pathlib import Path
from datetime import datetime, timedelta
from app.config.config import settings
from app.services.file_safety_service import FileSafetyService


class CleanupService:

    @staticmethod
    def cleanup():

        CleanupService.cleanup_uploads()

        CleanupService.cleanup_frames()

        CleanupService.cleanup_thumbnails()

        CleanupService.cleanup_old_jobs()

    @staticmethod
    def cleanup_uploads():

        uploads_dir = Path(
            settings.UPLOAD_FOLDER
        )

        if not uploads_dir.exists():
            return

        cutoff = (
            datetime.now()
            - timedelta(days=7)
        )

        for file in uploads_dir.iterdir():

            if not file.is_file():
                continue

            modified = datetime.fromtimestamp(
                file.stat().st_mtime
            )

            if modified < cutoff:

                FileSafetyService.safe_delete_file(file)

    @staticmethod
    def cleanup_frames():

        frames_dir = Path(
            settings.FRAME_FOLDER
        )

        if not frames_dir.exists():
            return

        cutoff = (
            datetime.now()
            - timedelta(days=1)
        )

        for folder in frames_dir.iterdir():

            if not folder.is_dir():
                continue

            modified = datetime.fromtimestamp(
                folder.stat().st_mtime
            )

            if modified < cutoff:

                FileSafetyService.safe_delete_file(folder)

    @staticmethod
    def cleanup_temp_file(
        file_path: str,
        job_id: str | None = None
    ):

        FileSafetyService.safe_delete_file(
            file_path,
            job_id=job_id
        )

    @staticmethod
    def cleanup_temp_folder(
        folder_path: str
    ):

        FileSafetyService.safe_delete_file(folder_path)

    @staticmethod
    def cleanup_old_jobs():

        jobs_dir = Path(
            settings.JOBS_FOLDER
        )

        if not jobs_dir.exists():
            return

        cutoff = (
            datetime.now()
            - timedelta(
                hours=settings.TEMP_CLEANUP_HOURS
            )
        )

        for job_folder in jobs_dir.iterdir():

            if not job_folder.is_dir():
                continue

            modified = datetime.fromtimestamp(
                job_folder.stat().st_mtime
            )

            if modified < cutoff:

                FileSafetyService.safe_delete_file(job_folder)

    @staticmethod
    def cleanup_old_temp_folders():

        cutoff = (
            datetime.now()
            - timedelta(
                hours=settings.TEMP_CLEANUP_HOURS
            )
        )

        scan_dirs = [
            Path(settings.FRAME_FOLDER),
            Path(settings.THUMBNAIL_FOLDER),
            Path(settings.UPLOAD_FOLDER),
        ]

        for scan_dir in scan_dirs:

            if not scan_dir.exists():
                continue

            for item in scan_dir.iterdir():

                modified = datetime.fromtimestamp(
                    item.stat().st_mtime
                )

                if modified >= cutoff:
                    continue

                FileSafetyService.safe_delete_file(item)

    @staticmethod
    def cleanup_thumbnails():

        thumbnails_dir = Path(
            settings.THUMBNAIL_FOLDER
        )

        if not thumbnails_dir.exists():
            return

        cutoff = (
            datetime.now()
            - timedelta(days=1)
        )

        for file in thumbnails_dir.iterdir():

            if not file.is_file():
                continue

            modified = datetime.fromtimestamp(
                file.stat().st_mtime
            )

            if modified < cutoff:

                FileSafetyService.safe_delete_file(file)