from pathlib import Path
from datetime import datetime, timedelta
import shutil
from app.config.config import settings
from app.services.logger_service import (
    LoggerService
)


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

                try:

                    file.unlink()

                    LoggerService.info(
                        f"Deleted upload: {file}"
                    )

                except Exception as error:

                    LoggerService.error(
                        f"Upload cleanup failed: {error}"
                    )

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

                try:

                    shutil.rmtree(folder)

                    LoggerService.info(
                        f"Deleted frame folder: {folder}"
                    )

                except Exception as error:

                    LoggerService.error(
                        f"Frame cleanup failed: {error}"
                    )

    @staticmethod
    def cleanup_temp_file(
        file_path: str,
        job_id: str | None = None
    ):

        path = Path(file_path)

        exists_before_delete = path.exists()

        if not exists_before_delete or not path.is_file():
            return

        try:

            path.unlink()

            LoggerService.info(
                f"Cleaned up temp file: {path}"
            )

        except Exception as error:

            LoggerService.error(
                f"Temp file cleanup failed: {error}"
            )

    @staticmethod
    def cleanup_temp_folder(
        folder_path: str
    ):

        path = Path(folder_path)

        if not path.exists() or not path.is_dir():
            return

        try:

            shutil.rmtree(path)

            LoggerService.info(
                f"Cleaned up temp folder: {path}"
            )

        except Exception as error:

            LoggerService.error(
                f"Temp folder cleanup failed: {error}"
            )

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

                try:

                    shutil.rmtree(job_folder)

                    LoggerService.info(
                        f"Deleted old job folder: {job_folder}"
                    )

                except Exception as error:

                    LoggerService.error(
                        f"Job folder cleanup failed: {error}"
                    )

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

                try:

                    if item.is_dir():

                        shutil.rmtree(item)

                    else:

                        item.unlink()

                    LoggerService.info(
                        f"Deleted old temp item: {item}"
                    )

                except Exception as error:

                    LoggerService.error(
                        f"Old temp cleanup failed: {error}"
                    )

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

                try:

                    file.unlink()

                    LoggerService.info(
                        f"Deleted thumbnail: {file}"
                    )

                except Exception as error:

                    LoggerService.error(
                        f"Thumbnail cleanup failed: {error}"
                    )