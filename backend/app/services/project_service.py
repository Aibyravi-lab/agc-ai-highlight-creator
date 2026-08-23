from datetime import datetime

from app.services.database_service import DatabaseService
from app.services.file_safety_service import FileSafetyService


class ProjectService:

    @classmethod
    def create_project(
        cls,
        user_id: int,
        job_id: str | None,
        original_video_name: str,
        thumbnail_path: str | None,
        horizontal_reel_path: str | None,
        vertical_reel_path: str | None = None,
        metadata_json_path: str | None = None,
        status: str = "completed"
    ) -> int:

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO projects (
                user_id,
                job_id,
                original_video_name,
                thumbnail_path,
                horizontal_reel_path,
                vertical_reel_path,
                metadata_json_path,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                job_id,
                original_video_name,
                thumbnail_path,
                horizontal_reel_path,
                vertical_reel_path,
                metadata_json_path,
                status,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        project_id = cursor.lastrowid

        connection.commit()
        connection.close()

        return project_id

    @classmethod
    def get_referenced_job_ids(cls) -> set[str]:
        """VED-MEDIA-001: CleanupService.cleanup_old_jobs() deletes
        storage/jobs/<job_id> purely by age, with no idea a projects row
        still points at that folder's media -- a completed project's
        job_id is a permanent, user-visible reference, not a regenerable
        temp artifact. This is the reference set cleanup must check before
        deleting anything.
        """

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT DISTINCT job_id FROM projects WHERE job_id IS NOT NULL"
        )

        rows = cursor.fetchall()

        connection.close()

        return {row[0] for row in rows}

    @classmethod
    def get_projects(
        cls,
        user_id: int
    ) -> list[dict]:

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
            """
            SELECT
                id, user_id, job_id,
                original_video_name,
                thumbnail_path,
                horizontal_reel_path,
                vertical_reel_path,
                metadata_json_path,
                status, created_at
            FROM projects
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        projects = cursor.fetchall()

        connection.close()

        for project in projects:
            cls._attach_media_availability(project)

        return projects

    @classmethod
    def get_project(
        cls,
        user_id: int,
        project_id: int
    ) -> dict | None:

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
            """
            SELECT
                id, user_id, job_id,
                original_video_name,
                thumbnail_path,
                horizontal_reel_path,
                vertical_reel_path,
                metadata_json_path,
                status, created_at
            FROM projects
            WHERE id = ? AND user_id = ?
            """,
            (project_id, user_id)
        )

        project = cursor.fetchone()

        connection.close()

        if project is not None:
            cls._attach_media_availability(project)

        return project

    @staticmethod
    def _attach_media_availability(project: dict) -> None:
        """VED-MEDIA-002: a projects row can persist a path whose file no
        longer exists on disk (see VED-MEDIA-001) -- the frontend needs
        an explicit signal to show "Media unavailable" instead of a
        silent broken thumbnail or no-op download, rather than assuming
        every persisted path is still servable. Only checks paths already
        present on this row (get_projects/get_project are both scoped to
        the requesting user_id), via FileSafetyService.is_available --
        never a client-supplied path, so this is not a new attack surface.
        Mutates `project` in place; does not touch the DB or the stored
        path values themselves.
        """

        project["thumbnail_available"] = (
            FileSafetyService.is_available(
                project.get("thumbnail_path")
            )
        )

        project["horizontal_reel_available"] = (
            FileSafetyService.is_available(
                project.get("horizontal_reel_path")
            )
        )

    @classmethod
    def delete_project(
        cls,
        user_id: int,
        project_id: int
    ) -> bool:

        project = cls.get_project(
            user_id=user_id,
            project_id=project_id
        )

        if project is None:
            return False

        asset_keys = [
            "thumbnail_path",
            "horizontal_reel_path",
            "vertical_reel_path",
            "metadata_json_path",
        ]

        for key in asset_keys:
            asset_path = project.get(key)
            if asset_path:
                FileSafetyService.safe_delete_file(asset_path)

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )

        deleted = cursor.rowcount > 0

        connection.commit()
        connection.close()

        return deleted
