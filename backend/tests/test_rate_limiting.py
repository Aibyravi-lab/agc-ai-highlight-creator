"""
AGC-069: global rate limiter coverage.

Exercises RateLimitService (the AGC-069 generalization of the AGC-063.6
per-IP throttle) both directly and through the endpoints that now use it:
login, register, upload, pipeline start, and payment verify. Also proves
the pre-existing password-reset limiter still works after being
refactored to delegate to RateLimitService instead of duplicating the
sliding-window logic.
"""

import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import auth as auth_router
from app.routers import payments as payments_router
from app.routers import pipeline as pipeline_router
from app.routers import upload as upload_router_module
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.password_reset_service import PasswordResetService
from app.services.rate_limit_service import RateLimitService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _fake_request(ip: str) -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=ip))


def _mark_verified(email: str) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE users SET email_verified = 1 WHERE email = ?", (email,)
    )
    connection.commit()
    connection.close()


class RateLimitServiceTests(unittest.TestCase):
    """Direct tests of the generic limiter: capacity and key isolation."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_blocks_after_max_attempts(self):
        for _ in range(3):
            self.assertFalse(
                RateLimitService.is_rate_limited(
                    "1.1.1.1", "some-endpoint", max_attempts=3, window_seconds=60
                )
            )

        self.assertTrue(
            RateLimitService.is_rate_limited(
                "1.1.1.1", "some-endpoint", max_attempts=3, window_seconds=60
            )
        )

    def test_independent_ips_do_not_affect_each_other(self):
        for _ in range(3):
            self.assertFalse(
                RateLimitService.is_rate_limited(
                    "1.1.1.1", "some-endpoint", max_attempts=3, window_seconds=60
                )
            )

        self.assertTrue(
            RateLimitService.is_rate_limited(
                "1.1.1.1", "some-endpoint", max_attempts=3, window_seconds=60
            )
        )

        # A different IP hitting the same endpoint has its own, untouched budget.
        self.assertFalse(
            RateLimitService.is_rate_limited(
                "2.2.2.2", "some-endpoint", max_attempts=3, window_seconds=60
            )
        )

    def test_different_users_do_not_affect_each_other(self):
        for _ in range(2):
            self.assertFalse(
                RateLimitService.is_rate_limited(
                    "user:1", "upload", max_attempts=2, window_seconds=60
                )
            )

        self.assertTrue(
            RateLimitService.is_rate_limited(
                "user:1", "upload", max_attempts=2, window_seconds=60
            )
        )

        self.assertFalse(
            RateLimitService.is_rate_limited(
                "user:2", "upload", max_attempts=2, window_seconds=60
            )
        )

    def test_independent_endpoints_do_not_affect_each_other(self):
        for _ in range(2):
            self.assertFalse(
                RateLimitService.is_rate_limited(
                    "9.9.9.9", "login", max_attempts=2, window_seconds=60
                )
            )

        self.assertTrue(
            RateLimitService.is_rate_limited(
                "9.9.9.9", "login", max_attempts=2, window_seconds=60
            )
        )

        # Same key, different endpoint scope -> independent budget.
        self.assertFalse(
            RateLimitService.is_rate_limited(
                "9.9.9.9", "register", max_attempts=2, window_seconds=60
            )
        )


class LoginRateLimitTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        AuthService.create_user("Test User", "login@test.com", "CorrectHorse123")
        _mark_verified("login@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_login_rate_limit_blocks_after_max_attempts_per_ip(self):
        body = auth_router.LoginRequest(
            email="login@test.com", password="CorrectHorse123"
        )
        request = _fake_request("5.5.5.5")

        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_PER_MINUTE):
            response = auth_router.login(body, request)
            self.assertTrue(response["success"])

        with self.assertRaises(HTTPException) as ctx:
            auth_router.login(body, request)

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertNotIn("rate_limit_attempts", str(ctx.exception.detail))

    def test_login_independent_ips_not_affected(self):
        body = auth_router.LoginRequest(
            email="login@test.com", password="CorrectHorse123"
        )

        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_PER_MINUTE):
            auth_router.login(body, _fake_request("6.6.6.6"))

        with self.assertRaises(HTTPException):
            auth_router.login(body, _fake_request("6.6.6.6"))

        # A different IP is unaffected by 6.6.6.6's exhausted budget.
        response = auth_router.login(body, _fake_request("7.7.7.7"))
        self.assertTrue(response["success"])


class RegisterRateLimitTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_register_rate_limit_blocks_after_max_attempts_per_ip(self):
        request = _fake_request("8.8.8.8")

        for i in range(settings.REGISTER_RATE_LIMIT_MAX_PER_MINUTE):
            body = auth_router.RegisterRequest(
                name="User",
                email=f"user{i}@test.com",
                password="ValidPass123",
            )
            response = auth_router.register(body, BackgroundTasks(), request)
            self.assertTrue(response["success"])

        body = auth_router.RegisterRequest(
            name="User",
            email="overflow@test.com",
            password="ValidPass123",
        )

        with self.assertRaises(HTTPException) as ctx:
            auth_router.register(body, BackgroundTasks(), request)

        self.assertEqual(ctx.exception.status_code, 429)


class UploadRateLimitTests(unittest.TestCase):

    _VALID_MP4_HEADER = bytes([0, 0, 0, 0x18]) + b"ftyp" + b"isom"

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self._upload_tmp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp_dir.cleanup()
        self._upload_tmp_dir.cleanup()

    def _client(self):
        app = FastAPI()
        app.include_router(upload_router_module.router)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": 42,
            "credits_remaining": 5,
        }
        return TestClient(app)

    def test_upload_rate_limit_blocks_after_max_attempts_per_user(self):
        with patch.object(settings, "UPLOAD_FOLDER", self._upload_tmp_dir.name), \
             patch.object(
                upload_router_module,
                "get_video_metadata",
                return_value={
                    "filename": "clip.mp4",
                    "duration_seconds": 10,
                    "resolution": "1920x1080",
                    "fps": 30.0,
                    "codec": "h264",
                    "file_size_mb": 1.0,
                },
             ):

            client = self._client()
            files = {
                "file": (
                    "clip.mp4",
                    io.BytesIO(self._VALID_MP4_HEADER + b"\x00" * 32),
                    "video/mp4",
                )
            }

            for _ in range(settings.UPLOAD_RATE_LIMIT_MAX_PER_HOUR):
                response = client.post("/upload/", files=files)
                self.assertEqual(response.status_code, 200)

            response = client.post("/upload/", files=files)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(
                response.json()["detail"]["code"],
                upload_router_module.UploadError.RATE_LIMITED,
            )


class PipelineStartRateLimitTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _start(self, user_id: int):
        current_user = {"id": user_id, "credits_remaining": 5}

        with patch.object(
            pipeline_router.VideoPathService,
            "validate_upload_path",
            side_effect=lambda path: path,
        ), patch.object(
            pipeline_router.BackgroundJobService,
            "is_accepting_jobs",
            return_value=True,
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
            pipeline_router.BackgroundJobService,
            "start_job",
        ):
            return pipeline_router.start_video_processing(
                "video.mp4", current_user
            )

    def test_pipeline_start_rate_limit_blocks_after_max_attempts_per_user(self):
        for _ in range(settings.PIPELINE_START_RATE_LIMIT_MAX_PER_HOUR):
            result = self._start(user_id=1)
            self.assertTrue(result["success"])

        with self.assertRaises(HTTPException) as ctx:
            self._start(user_id=1)

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(
            ctx.exception.detail["code"], pipeline_router.PipelineError.RATE_LIMITED
        )

    def test_pipeline_start_different_users_not_affected(self):
        for _ in range(settings.PIPELINE_START_RATE_LIMIT_MAX_PER_HOUR):
            self._start(user_id=1)

        with self.assertRaises(HTTPException):
            self._start(user_id=1)

        # A different user_id has its own untouched budget.
        result = self._start(user_id=2)
        self.assertTrue(result["success"])


class PaymentVerifyRateLimitTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _verify(self, user_id: int, payment_id: str):
        body = payments_router.VerifyPaymentRequest(
            razorpay_order_id=f"order_{payment_id}",
            razorpay_payment_id=payment_id,
            razorpay_signature="sig",
        )
        current_user = {"id": user_id}

        with patch.object(
            payments_router.PaymentService, "verify_payment", return_value=None
        ), patch.object(
            payments_router.PaymentService,
            "process_verified_payment",
            return_value={"plan": "PRO", "status": "ACTIVE"},
        ):
            return payments_router.verify_payment(body, current_user)

    def test_payment_verify_rate_limit_blocks_after_max_attempts_per_user(self):
        for i in range(settings.PAYMENT_VERIFY_RATE_LIMIT_MAX_PER_MINUTE):
            result = self._verify(user_id=1, payment_id=f"pay_{i}")
            self.assertTrue(result["success"])

        with self.assertRaises(HTTPException) as ctx:
            self._verify(user_id=1, payment_id="pay_overflow")

        self.assertEqual(ctx.exception.status_code, 429)


class PasswordResetLimiterStillWorksTests(unittest.TestCase):
    """
    AGC-063.6 regression coverage: PasswordResetService.is_ip_throttled
    was refactored (AGC-069) to delegate to the new generic
    RateLimitService instead of duplicating the sliding-window SQL.
    Limits must be unchanged.
    """

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_service_level_limit_unchanged(self):
        for _ in range(settings.PASSWORD_RESET_ATTEMPT_MAX_PER_IP):
            self.assertFalse(
                PasswordResetService.is_ip_throttled("3.3.3.3", "forgot-password")
            )

        self.assertTrue(
            PasswordResetService.is_ip_throttled("3.3.3.3", "forgot-password")
        )

    def test_forgot_password_endpoint_still_rate_limited(self):
        request = _fake_request("4.4.4.4")
        body = auth_router.ForgotPasswordRequest(email="nobody@test.com")

        for _ in range(settings.PASSWORD_RESET_ATTEMPT_MAX_PER_IP):
            background_tasks = BackgroundTasks()
            response = auth_router.forgot_password(body, background_tasks, request)
            self.assertTrue(response["success"])

        with self.assertRaises(HTTPException) as ctx:
            auth_router.forgot_password(body, BackgroundTasks(), request)

        self.assertEqual(ctx.exception.status_code, 429)

    def test_forgot_and_reset_password_endpoints_have_independent_budgets(self):
        # Same IP, different endpoint scopes -> exhausting forgot-password
        # must not affect reset-password (each passes its own "endpoint"
        # label to the shared limiter).
        request = _fake_request("2.2.2.2")

        for _ in range(settings.PASSWORD_RESET_ATTEMPT_MAX_PER_IP):
            PasswordResetService.is_ip_throttled("2.2.2.2", "forgot-password")

        self.assertTrue(
            PasswordResetService.is_ip_throttled("2.2.2.2", "forgot-password")
        )
        self.assertFalse(
            PasswordResetService.is_ip_throttled("2.2.2.2", "reset-password")
        )


if __name__ == "__main__":
    unittest.main()
