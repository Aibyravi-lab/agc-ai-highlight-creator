from datetime import datetime
from pathlib import Path

from app.config.config import settings
from app.services.database_service import DatabaseService


class HistoryService:

    @classmethod
    def add_history(
        cls,
        video_name: str,
        reel_path: str,
        highlights_count: int,
        user_id: int
    ):

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO history (
                user_id,
                video_name,
                date,
                reel_path,
                highlights_count
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                video_name,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                reel_path,
                highlights_count
            )
        )

        connection.commit()
        connection.close()

    @classmethod
    def get_history(
        cls,
        user_id: int
    ):

        connection = DatabaseService.get_connection()

        connection.row_factory = (
            lambda cursor, row: {
                col[0]: row[idx]
                for idx, col in enumerate(
                    cursor.description
                )
            }
        )

        cursor = connection.cursor()

        cursor.execute(
            "SELECT video_name, date, reel_path, highlights_count"
            " FROM history WHERE user_id = ?"
            " ORDER BY date DESC",
            (user_id,)
        )

        history = cursor.fetchall()

        connection.close()

        return history

    @classmethod
    def get_referenced_job_ids(cls) -> set[str]:
        """VED-MEDIA-001 CHECK 1: history has no job_id column (see the
        VED-P1-012 note on add_history's caller) -- but reel_path is
        written from the exact same JOBS_FOLDER/<job_id>/reels/... path
        ReelService/JobStorageService produce for a project's
        horizontal_reel_path (pipeline_service.py's History Registration
        step runs immediately before Project Registration, from the same
        `final_reel` value). If Project Registration then fails, History
        is left as the *only* persistent, user-visible reference to that
        job's media -- so cleanup must derive job_id from the path itself
        rather than assume every History row has a matching Projects row.
        """

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT reel_path FROM history WHERE reel_path IS NOT NULL"
        )

        rows = cursor.fetchall()

        connection.close()

        try:
            jobs_root = Path(settings.JOBS_FOLDER).resolve()
        except (OSError, RuntimeError):
            return set()

        referenced: set[str] = set()

        for (reel_path,) in rows:

            if not reel_path:
                continue

            try:
                resolved = Path(reel_path).resolve(strict=False)
                relative = resolved.relative_to(jobs_root)
            except (OSError, RuntimeError, ValueError):
                continue

            if relative.parts:
                referenced.add(relative.parts[0])

        return referenced
