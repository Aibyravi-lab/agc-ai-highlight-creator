import json
import uuid

from datetime import datetime

from app.services.database_service import (
    DatabaseService
)


class JobService:

    @classmethod
    def create_job(
        cls,
        user_id: int
    ):

        job_id = str(
            uuid.uuid4()
        )

        created_at = (
            datetime.utcnow()
            .isoformat()
        )

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO jobs (
                job_id,
                user_id,
                status,
                progress,
                message,
                result,
                error,
                created_at,
                started_at,
                completed_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                job_id,
                user_id,
                "pending",
                0,
                "Job Created",
                None,
                None,
                created_at,
                None,
                None
            )
        )

        connection.commit()
        connection.close()

        return job_id

    @classmethod
    def get_job(
        cls,
        job_id: str
    ):

        connection = (
            DatabaseService.get_connection()
        )

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
            SELECT *
            FROM jobs
            WHERE job_id = ?
            """,
            (job_id,)
        )

        job = cursor.fetchone()

        connection.close()

        if (
            job and
            job["result"]
        ):
            try:

                job["result"] = (
                    json.loads(
                        job["result"]
                    )
                )

            except Exception:
                pass

        return job

    @classmethod
    def get_all_jobs(
        cls,
        user_id: int
    ):

        connection = (
            DatabaseService.get_connection()
        )

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
            SELECT *
            FROM jobs
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        jobs = cursor.fetchall()

        connection.close()

        for job in jobs:

            if job["result"]:

                try:

                    job["result"] = (
                        json.loads(
                            job["result"]
                        )
                    )

                except Exception:
                    pass

        return jobs

    @classmethod
    def update_job(
        cls,
        job_id: str,
        progress: int,
        message: str,
        status: str = "processing"
    ):

        job = cls.get_job(
            job_id
        )

        if not job:
            return

        started_at = (
            job["started_at"]
        )

        if started_at is None:

            started_at = (
                datetime.utcnow()
                .isoformat()
            )

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                progress = ?,
                message = ?,
                started_at = ?
            WHERE job_id = ?
            """,
            (
                status,
                progress,
                message,
                started_at,
                job_id
            )
        )

        connection.commit()
        connection.close()

    @classmethod
    def complete_job(
        cls,
        job_id: str,
        result: dict
    ):

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                progress = ?,
                message = ?,
                result = ?,
                completed_at = ?
            WHERE job_id = ?
            """,
            (
                "completed",
                100,
                "Completed",
                json.dumps(
                    result
                ),
                datetime.utcnow()
                .isoformat(),
                job_id
            )
        )

        connection.commit()
        connection.close()

    @classmethod
    def fail_job(
        cls,
        job_id: str,
        error: str
    ):

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE jobs
            SET
                status = ?,
                message = ?,
                error = ?,
                completed_at = ?
            WHERE job_id = ?
            """,
            (
                "failed",
                "Failed",
                error,
                datetime.utcnow()
                .isoformat(),
                job_id
            )
        )

        connection.commit()
        connection.close()

    @classmethod
    def get_job_stats(
        cls,
        user_id: int
    ):

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_jobs,

                SUM(
                    CASE
                    WHEN status='pending'
                    THEN 1
                    ELSE 0
                    END
                ) as pending_jobs,

                SUM(
                    CASE
                    WHEN status='processing'
                    THEN 1
                    ELSE 0
                    END
                ) as processing_jobs,

                SUM(
                    CASE
                    WHEN status='completed'
                    THEN 1
                    ELSE 0
                    END
                ) as completed_jobs,

                SUM(
                    CASE
                    WHEN status='failed'
                    THEN 1
                    ELSE 0
                    END
                ) as failed_jobs

            FROM jobs
            WHERE user_id = ?
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        connection.close()

        return {

            "total_jobs":
            row[0] or 0,

            "pending_jobs":
            row[1] or 0,

            "processing_jobs":
            row[2] or 0,

            "completed_jobs":
            row[3] or 0,

            "failed_jobs":
            row[4] or 0

        }

    @classmethod
    def get_user_active_progress(
        cls,
        user_id: int
    ) -> dict:

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT progress, message
            FROM jobs
            WHERE user_id = ?
              AND status = 'processing'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        connection.close()

        if row:
            return {
                "progress": row[0] or 0,
                "status": row[1] or ""
            }

        return {
            "progress": 0,
            "status": ""
        }

    @classmethod
    def user_owns_file(
        cls,
        user_id: int,
        file_path: str
    ) -> bool:

        normalized = file_path.replace("\\", "/")

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT result
            FROM jobs
            WHERE user_id = ?
              AND result IS NOT NULL
            """,
            (user_id,)
        )

        rows = cursor.fetchall()

        connection.close()

        for row in rows:

            try:

                result = json.loads(row[0])

                paths = cls._collect_result_paths(
                    result
                )

                if normalized in paths:
                    return True

            except Exception:
                pass

        return False

    @classmethod
    def get_running_job_count(
        cls,
        user_id: int
    ) -> int:

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM jobs
            WHERE user_id = ?
              AND status IN ('pending', 'processing')
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        connection.close()

        return row[0] if row else 0

    @classmethod
    def _collect_result_paths(
        cls,
        result: dict
    ) -> set:

        paths: set = set()

        for key in (
            "final_reel",
            "vertical_reel",
            "thumbnail",
            "result_json",
            "captioned_reel"
        ):
            value = result.get(key)
            if value and isinstance(value, str):
                paths.add(
                    value.replace("\\", "/")
                )

        for highlight in (
            result.get("all_highlights") or []
        ):
            for key in (
                "clip_path",
                "thumbnail_path"
            ):
                value = highlight.get(key)
                if value and isinstance(value, str):
                    paths.add(
                        value.replace("\\", "/")
                    )

        return paths