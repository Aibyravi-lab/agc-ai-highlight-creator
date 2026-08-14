import json
import uuid

from datetime import datetime

from app.services.database_service import (
    DatabaseService
)
from app.services.auth_service import AuthService
from app.services.subscription_service import SubscriptionService
from app.services.job_storage_service import JobStorageService
from app.services.logger_service import LoggerService
from app.services.history_service import HistoryService
from app.services.project_service import ProjectService


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
    def load_valid_result_artifact(
        cls,
        job_id: str
    ) -> dict | None:
        """VED-P1-011: the authoritative signal that a job's pipeline
        actually finished is a valid result.json on disk (written by
        ResultExportService before the terminal DB commit — see the
        VED-P1-011 audit's failure-window trace), not progress=100,
        message="Completed", or the existence of history/project rows.
        Returns the parsed result payload, or None if no valid completed
        result exists for this job.
        """

        result_path = (
            JobStorageService.job_dir(job_id)
            / "results"
            / "result.json"
        )

        if not result_path.exists():
            return None

        try:

            with open(
                result_path,
                "r",
                encoding="utf-8"
            ) as file:

                result = json.load(file)

        except (OSError, json.JSONDecodeError) as error:

            LoggerService.error(
                "event=result_artifact_invalid "
                f"job_id={job_id} reason=unreadable error={error}",
                job_id=job_id
            )

            return None

        if not isinstance(result, dict):

            LoggerService.error(
                "event=result_artifact_invalid "
                f"job_id={job_id} reason=not_an_object",
                job_id=job_id
            )

            return None

        required_fields = (
            "highlights",
            "final_reel",
            "stats",
            "result_json"
        )

        if not all(field in result for field in required_fields):

            LoggerService.error(
                "event=result_artifact_invalid "
                f"job_id={job_id} reason=missing_required_fields",
                job_id=job_id
            )

            return None

        if (
            not isinstance(result.get("highlights"), list)
            or not result["highlights"]
        ):

            LoggerService.error(
                "event=result_artifact_invalid "
                f"job_id={job_id} reason=empty_highlights",
                job_id=job_id
            )

            return None

        if (
            not isinstance(result.get("final_reel"), str)
            or not result["final_reel"]
        ):

            LoggerService.error(
                "event=result_artifact_invalid "
                f"job_id={job_id} reason=missing_final_reel",
                job_id=job_id
            )

            return None

        return result

    @classmethod
    def _commit_recovered_job(
        cls,
        job_id: str,
        result: dict
    ) -> bool:
        """VED-P1-011 CTO review: complete_job()'s commit can itself fail
        transiently (SQLite contention, disk I/O) while recovering a job
        during startup reconciliation, after its result has already been
        verified valid. Letting that exception propagate out of
        reconcile_interrupted_jobs (as it did prior to this fix) would
        crash the entire application startup over a single job's
        recoverable commit failure — a worse outage than the false
        failure this feature closes. One immediate retry lets a
        transient failure self-heal within the same reconciliation pass;
        if it still fails, the job is left "processing" rather than
        failed or refunded — the next reconciliation pass (a future
        restart) will find the same valid result.json and retry it.
        Deliberately catches Exception, not BaseException.
        """

        try:

            cls.complete_job(
                job_id=job_id,
                result=result
            )

            return True

        except Exception as first_error:

            LoggerService.error(
                "event=complete_job_commit_failed "
                f"job_id={job_id} attempt=1 error={first_error} "
                "context=reconciliation",
                job_id=job_id
            )

        try:

            cls.complete_job(
                job_id=job_id,
                result=result
            )

            return True

        except Exception as retry_error:

            LoggerService.error(
                "event=complete_job_commit_failed "
                f"job_id={job_id} attempt=2 error={retry_error} "
                "context=reconciliation outcome=left_recoverable",
                job_id=job_id
            )

            return False

    @classmethod
    def _register_recovered_artifacts(
        cls,
        job_id: str,
        user_id: int | None,
        result: dict
    ) -> None:
        """VED-P1-012: a job recovered via reconcile_interrupted_jobs is
        marked completed from its on-disk result.json alone (see
        load_valid_result_artifact) — but that snapshot predates
        HistoryService.add_history/ProjectService.create_project in the
        normal pipeline (see pipeline_service.py's post-export
        registration step), so a recovered job never gets those rows.
        Without this, the job is "completed" but permanently invisible
        in the user's History/Projects lists. This is called only after
        _commit_recovered_job has confirmed the job row itself is
        completed, and is fully isolated: any failure here is logged and
        swallowed — it must never re-fail a job that already succeeded,
        never trigger a refund, and never crash startup reconciliation.

        The original uploaded filename is not recoverable from either
        the jobs table or result.json (neither persists it), so
        recovered entries use the deterministic fallback
        "Recovered Job <job_id>" (CTO MVP decision, VED-P1-012) —
        intentionally not a database migration.
        """

        if user_id is None:
            return

        fallback_name = f"Recovered Job {job_id}"

        try:

            connection = (
                DatabaseService.get_connection()
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id
                FROM projects
                WHERE job_id = ?
                """,
                (job_id,)
            )

            existing_project = cursor.fetchone()

            connection.close()

            if existing_project is None:

                ProjectService.create_project(
                    user_id=user_id,
                    job_id=job_id,
                    original_video_name=fallback_name,
                    thumbnail_path=result.get("thumbnail"),
                    horizontal_reel_path=result.get("final_reel"),
                    vertical_reel_path=result.get("vertical_reel") or None,
                    metadata_json_path=result.get("result_json") or None
                )

            # VED-P1-012: the history table has no job_id column, so it
            # cannot be matched back to a specific job the way projects
            # can — this is a best-effort application-level guard, not a
            # schema-guaranteed one. It relies on the fallback name above
            # being deterministic per job_id (and not colliding with a
            # real uploaded filename) to avoid duplicate rows across
            # repeated registration attempts.
            connection = (
                DatabaseService.get_connection()
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT 1
                FROM history
                WHERE user_id = ?
                  AND video_name = ?
                """,
                (user_id, fallback_name)
            )

            existing_history = cursor.fetchone()

            connection.close()

            if existing_history is None:

                HistoryService.add_history(
                    video_name=fallback_name,
                    reel_path=result.get("final_reel"),
                    highlights_count=len(
                        result.get("highlights", [])
                    ),
                    user_id=user_id
                )

            LoggerService.info(
                "event=recovered_artifacts_registered "
                f"job_id={job_id}",
                job_id=job_id
            )

        except Exception as registration_error:

            LoggerService.error(
                "event=recovered_artifact_registration_failed "
                f"job_id={job_id} error={registration_error}",
                job_id=job_id
            )

            return

    @classmethod
    def reconcile_interrupted_jobs(cls):
        """VED-P1-011: a job can finish all pipeline work — result.json
        written, history/project rows persisted, progress=100 — and still
        be sitting at status='processing' if the process crashes before
        complete_job()'s commit lands (see the VED-P1-011 audit). Blindly
        marking every pending/processing job failed-and-refunded on
        restart (the pre-VED-P1-011 behavior) turned that narrow timing
        gap into a false failure and a wrongful refund for real,
        completed work. Each interrupted job is now classified
        individually: a valid result.json recovers it as completed with
        no refund; anything else preserves the original fail+refund path.
        """

        connection = (
            DatabaseService.get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT job_id, user_id
            FROM jobs
            WHERE status IN ('pending', 'processing')
            """
        )

        interrupted = cursor.fetchall()

        connection.close()

        reconciled_failed = 0

        for job_id, user_id in interrupted:

            recovered_result = cls.load_valid_result_artifact(
                job_id
            )

            if recovered_result is not None:

                if cls._commit_recovered_job(
                    job_id=job_id,
                    result=recovered_result
                ):

                    LoggerService.info(
                        "event=job_recovered_on_reconciliation "
                        f"job_id={job_id}",
                        job_id=job_id
                    )

                    # VED-P1-012: only register History/Project rows once
                    # the job row itself is confirmed completed — never
                    # while the commit is still pending a retry, so this
                    # is naturally re-attempted on a future reconciliation
                    # pass if the job wasn't committed yet this time.
                    cls._register_recovered_artifacts(
                        job_id=job_id,
                        user_id=user_id,
                        result=recovered_result
                    )

                # Whether the commit succeeded or is still pending after
                # a failed retry, this job is never failed or refunded
                # here — a confirmed-valid result must never be treated
                # as a genuine pipeline failure.
                continue

            cls.fail_job(
                job_id=job_id,
                error="Interrupted by server restart"
            )

            reconciled_failed += 1

            # A credit was deducted when this job started, unless the
            # owner was an active PRO subscriber (who is never charged a
            # credit); since the job never reached a completed/recovered
            # state on its own (server restart cut it off mid-flight with
            # no completed result to recover), refund the credit it
            # consumed.
            if user_id is not None and not SubscriptionService.is_pro_active(user_id):
                AuthService.refund_credit(user_id)

        return reconciled_failed

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

        # VED-P1-012: a normally-completed job's stored result has
        # "all_highlights"; a job recovered from result.json (see
        # load_valid_result_artifact) only has "highlights" — both must
        # authorize their own highlight clip/thumbnail paths.
        for highlight in (
            result.get("all_highlights")
            or result.get("highlights")
            or []
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