"""AGC-084: maintenance mode enforcement on POST /pipeline/start.

The maintenance check must occur before rate-limit consumption, credit
deduction, JobService.create_job(), and BackgroundJobService.start_job() —
a maintenance-ON request must create no job and submit no worker. Normal
behavior when maintenance is OFF must be completely unaffected.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.routers import pipeline as pipeline_router
from app.services.database_service import DatabaseService
from app.services.job_service import JobService


class PipelineMaintenanceModeTests(unittest.TestCase):

    def setUp(self):
        self.current_user = {"id": 1, "credits_remaining": 5}

    def test_pipeline_start_blocked_with_503_when_maintenance_on(self):
        with patch.object(
            pipeline_router.MaintenanceService,
            "is_maintenance_mode",
            return_value=True,
        ), patch.object(
            pipeline_router.VideoPathService, "validate_upload_path"
        ) as mock_validate, patch.object(
            pipeline_router.RateLimitService, "is_rate_limited"
        ) as mock_rate_limited, patch.object(
            pipeline_router.AuthService, "deduct_credit"
        ) as mock_deduct_credit, patch.object(
            pipeline_router.JobService, "create_job"
        ) as mock_create_job, patch.object(
            pipeline_router.BackgroundJobService, "start_job"
        ) as mock_start_job:

            with self.assertRaises(HTTPException) as ctx:
                pipeline_router.start_video_processing(
                    "video.mp4", self.current_user
                )

            self.assertEqual(ctx.exception.status_code, 503)
            self.assertEqual(
                ctx.exception.detail["code"],
                pipeline_router.PipelineError.MAINTENANCE_MODE,
            )
            self.assertEqual(
                ctx.exception.detail["message"],
                pipeline_router.MaintenanceService.MESSAGE,
            )
            self.assertEqual(
                ctx.exception.headers.get("Retry-After"), "300"
            )

            # No downstream side effect ran: no path validation, no rate
            # limiting, no credit deduction, no job created, no worker
            # submitted.
            mock_validate.assert_not_called()
            mock_rate_limited.assert_not_called()
            mock_deduct_credit.assert_not_called()
            mock_create_job.assert_not_called()
            mock_start_job.assert_not_called()

    def test_pipeline_start_succeeds_normally_when_maintenance_off(self):
        with patch.object(
            pipeline_router.MaintenanceService,
            "is_maintenance_mode",
            return_value=False,
        ), patch.object(
            pipeline_router.VideoPathService,
            "validate_upload_path",
            side_effect=lambda path: path,
        ), patch.object(
            pipeline_router.BackgroundJobService,
            "is_accepting_jobs",
            return_value=True,
        ), patch.object(
            pipeline_router.RateLimitService,
            "is_rate_limited",
            return_value=False,
        ), patch.object(
            pipeline_router.JobService,
            "get_running_job_count",
            return_value=0,
        ), patch.object(
            pipeline_router.SubscriptionService,
            "is_pro_active",
            return_value=True,
        ), patch.object(
            pipeline_router.JobService,
            "create_job",
            return_value="job-1",
        ), patch.object(
            pipeline_router.BackgroundJobService, "start_job"
        ) as mock_start_job:

            result = pipeline_router.start_video_processing(
                "video.mp4", self.current_user
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["job_id"], "job-1")
            mock_start_job.assert_called_once()


class ExistingJobsUnaffectedByMaintenanceToggleTests(unittest.TestCase):
    """AGC-084: toggling the maintenance flag must not touch jobs that
    already exist — the flag only gates *new* /pipeline/start requests.
    """

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        DatabaseService.DB_DIR = Path(self._tmp_dir.name)
        DatabaseService.DB_PATH = Path(self._tmp_dir.name) / "test_agc.db"
        DatabaseService.initialize()

        self.job_id = JobService.create_job(user_id=1)
        JobService.update_job(
            job_id=self.job_id, progress=42, message="Detecting Highlights"
        )

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_read_endpoints_unaffected_when_maintenance_on(self):
        current_user = {"id": 1, "credits_remaining": 5}

        with patch.object(
            pipeline_router.MaintenanceService,
            "is_maintenance_mode",
            return_value=True,
        ):
            job_status = pipeline_router.get_job_status(
                self.job_id, current_user
            )
            all_jobs = pipeline_router.get_all_jobs(current_user)

        self.assertTrue(job_status["success"])
        self.assertEqual(job_status["data"]["status"], "processing")
        self.assertEqual(all_jobs["count"], 1)

    def test_job_still_completes_via_job_service_when_maintenance_on(self):
        with patch.object(
            pipeline_router.MaintenanceService,
            "is_maintenance_mode",
            return_value=True,
        ):
            # JobService/BackgroundJobService completion path is untouched
            # by AGC-084 — the flag was never wired into it.
            JobService.complete_job(self.job_id, result={"ok": True})

        job = JobService.get_job(self.job_id)
        self.assertEqual(job["status"], "completed")


if __name__ == "__main__":
    unittest.main()
