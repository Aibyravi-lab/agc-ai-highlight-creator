from pathlib import Path
from datetime import datetime, timedelta
import shutil

from app.services.logger_service import (
    LoggerService
)


class CleanupService:

    @staticmethod
    def cleanup():

        CleanupService.cleanup_uploads()

        CleanupService.cleanup_frames()

        CleanupService.cleanup_thumbnails()

    @staticmethod
    def cleanup_uploads():

        uploads_dir = Path(
            "storage/uploads"
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
            "storage/frames"
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
    def cleanup_thumbnails():

        thumbnails_dir = Path(
            "storage/thumbnails"
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