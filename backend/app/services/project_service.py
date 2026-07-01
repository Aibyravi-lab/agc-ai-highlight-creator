from datetime import datetime
from pathlib import Path

from app.services.database_service import DatabaseService


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

        return project

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
                try:
                    Path(asset_path).unlink(missing_ok=True)
                except Exception:
                    pass

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
