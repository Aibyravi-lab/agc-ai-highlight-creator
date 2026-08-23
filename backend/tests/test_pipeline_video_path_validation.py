import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.config.config import settings
from app.routers import pipeline as pipeline_router


class PipelineVideoPathValidationTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp_dir.name)

        self.uploads = self.root / "uploads"
        self.outside = self.root / "outside"

        for folder in (self.uploads, self.outside):
            folder.mkdir(parents=True, exist_ok=True)

        self._patcher = patch.object(
            settings, "UPLOAD_FOLDER", str(self.uploads)
        )
        self._patcher.start()

        self.current_user = {"id": 1, "credits_remaining": 5}

    def tearDown(self):
        self._patcher.stop()
        self._tmp_dir.cleanup()

    def _assert_blocked(self, video_path):

        with patch.object(
            pipeline_router.JobService, "create_job"
        ) as mock_create_job, patch.object(
            pipeline_router.BackgroundJobService, "start_job"
        ) as mock_start_job, patch.object(
            pipeline_router.AuthService, "deduct_credit"
        ) as mock_deduct_credit:

            with self.assertRaises(HTTPException) as ctx:
                pipeline_router.start_video_processing(
                    video_path, self.current_user
                )

            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(
                ctx.exception.detail["code"],
                pipeline_router.PipelineError.INVALID_VIDEO_PATH
            )

            mock_deduct_credit.assert_not_called()
            mock_create_job.assert_not_called()
            mock_start_job.assert_not_called()

    def test_path_traversal_blocked(self):
        victim = self.outside / "secret.txt"
        victim.write_text("secret")

        self._assert_blocked(
            str(self.uploads / ".." / "outside" / "secret.txt")
        )

    def test_file_scheme_blocked(self):
        self._assert_blocked("file:///etc/passwd")

    def test_localhost_blocked(self):
        self._assert_blocked("http://localhost")

    def test_loopback_ip_blocked(self):
        self._assert_blocked("http://127.0.0.1")

    def test_private_ip_blocked(self):
        self._assert_blocked("http://10.0.0.5")

    def test_metadata_endpoint_blocked(self):
        self._assert_blocked("http://169.254.169.254")

    def test_valid_uploaded_video_starts_pipeline(self):
        video = self.uploads / "1_abc123_clip.mp4"
        video.write_bytes(b"data")

        with patch.object(
            pipeline_router.BackgroundJobService,
            "is_accepting_jobs",
            return_value=True
        ), patch.object(
            pipeline_router.RateLimitService,
            "is_rate_limited",
            return_value=False
        ), patch.object(
            pipeline_router.JobService,
            "get_running_job_count",
            return_value=0
        ), patch.object(
            pipeline_router.SubscriptionService,
            "is_pro_active",
            return_value=True
        ), patch.object(
            pipeline_router.JobService,
            "create_job",
            return_value="job-1"
        ), patch.object(
            pipeline_router.BackgroundJobService,
            "start_job"
        ) as mock_start_job:

            result = pipeline_router.start_video_processing(
                str(video), self.current_user
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["job_id"], "job-1")

            mock_start_job.assert_called_once()
            _, kwargs = mock_start_job.call_args
            self.assertEqual(
                kwargs["video_path"],
                str(video.resolve())
            )

    # ── VED-SEC-001: cross-user ownership enforcement ───────────────

    def test_other_users_video_path_rejected(self):
        # User 1's own uploaded file — current_user is id=1, but the
        # file belongs to user 2 (the "victim").
        victim_video = self.uploads / "2_abc123_clip.mp4"
        victim_video.write_bytes(b"data")

        self._assert_blocked(str(victim_video))

    def test_ownership_rejection_returns_same_shape_as_invalid_path(self):
        # No cross-user leakage: a real file owned by someone else must
        # produce the exact same error code/message shape as a bogus path.
        victim_video = self.uploads / "2_abc123_clip.mp4"
        victim_video.write_bytes(b"data")

        with patch.object(
            pipeline_router.JobService, "create_job"
        ), patch.object(
            pipeline_router.BackgroundJobService, "start_job"
        ), patch.object(
            pipeline_router.AuthService, "deduct_credit"
        ):
            with self.assertRaises(HTTPException) as owned_by_other_ctx:
                pipeline_router.start_video_processing(
                    str(victim_video), self.current_user
                )

            with self.assertRaises(HTTPException) as nonexistent_ctx:
                pipeline_router.start_video_processing(
                    str(self.uploads / "2_never_existed.mp4"),
                    self.current_user
                )

        self.assertEqual(
            owned_by_other_ctx.exception.detail,
            nonexistent_ctx.exception.detail
        )


if __name__ == "__main__":
    unittest.main()
