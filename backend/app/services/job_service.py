import json
import uuid

from datetime import datetime

from app.services.database_service import (
    DatabaseService
)


class JobService:

    @classmethod
    def create_job(
        cls
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
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                job_id,
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
        cls
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
            ORDER BY created_at DESC
            """
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
        cls
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
            """
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