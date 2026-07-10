import shutil
from pathlib import Path

from app.config.config import settings
from app.services.logger_service import LoggerService


class FileSafetyService:
    """Single choke point for deleting application-owned storage files.

    Every delete must resolve inside one of the configured storage
    folders. Anything else (traversal, absolute paths outside storage,
    symlinks resolving outside storage) is refused and logged.
    """

    @classmethod
    def _allowed_roots(cls) -> list[Path]:

        folders = {
            settings.UPLOAD_FOLDER,
            settings.OUTPUT_FOLDER,
            settings.FRAME_FOLDER,
            settings.THUMBNAIL_FOLDER,
            settings.HIGHLIGHT_FOLDER,
            settings.RESULTS_FOLDER,
            settings.JOBS_FOLDER,
        }

        return [Path(folder).resolve() for folder in folders]

    @classmethod
    def _is_safe_target(cls, target: Path) -> bool:

        try:
            resolved = target.resolve(strict=False)
        except (OSError, RuntimeError):
            return False

        for root in cls._allowed_roots():

            if resolved == root:
                # Never allow deleting a storage root itself.
                return False

            if root in resolved.parents:
                return True

        return False

    @classmethod
    def safe_delete_file(
        cls,
        path: str | Path,
        *,
        job_id: str | None = None
    ) -> bool:
        """Delete a file or directory if it is inside approved storage.

        Missing targets are treated as already-deleted (no error).
        Returns False if the delete was blocked or failed.
        """

        if path is None or (
            isinstance(path, str) and not path.strip()
        ):

            LoggerService.error(
                f"Blocked unsafe delete: {path!r}",
                job_id=job_id
            )

            return False

        try:
            target = Path(path)
        except (TypeError, ValueError):

            LoggerService.error(
                f"Blocked unsafe delete: {path!r}",
                job_id=job_id
            )

            return False

        if not cls._is_safe_target(target):

            LoggerService.error(
                f"Blocked unsafe delete: {target}",
                job_id=job_id
            )

            return False

        try:

            if target.is_symlink() or target.is_file():

                target.unlink(missing_ok=True)

                LoggerService.info(
                    f"Deleted file: {target}",
                    job_id=job_id
                )

            elif target.is_dir():

                shutil.rmtree(target)

                LoggerService.info(
                    f"Deleted directory: {target}",
                    job_id=job_id
                )

            return True

        except Exception as error:

            LoggerService.error(
                f"Delete failed: {target} | {error}",
                job_id=job_id
            )

            return False
