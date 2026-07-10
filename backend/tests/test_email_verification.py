"""
AGC-070: email verification coverage.

Exercises EmailVerificationService directly (token issuance, single-use
consumption, expiry) and through the auth endpoints it gates: register no
longer auto-logs in and always issues a verification email, login is
rejected for unverified users, and credits (granted at registration via
the existing credits_remaining default) are only reachable once a user
can actually log in and call an authenticated endpoint.

Mirrors the isolated-sqlite-db and direct-router-call conventions already
used by test_rate_limiting.py and test_subscription_expiry.py.
"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException

from app.routers import auth as auth_router
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.email_verification_service import EmailVerificationService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _fake_request(ip: str = "1.2.3.4") -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=ip))


class RegisterSendsVerificationEmailTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_register_does_not_auto_login(self):
        body = auth_router.RegisterRequest(
            name="User", email="new@test.com", password="ValidPass123"
        )

        with patch.object(EmailVerificationService, "send_verification_email"):
            response = auth_router.register(body, BackgroundTasks(), _fake_request())

        self.assertTrue(response["success"])
        self.assertNotIn("access_token", response)
        self.assertFalse(response["user"]["email_verified"])

    def test_register_queues_verification_email(self):
        body = auth_router.RegisterRequest(
            name="User", email="new2@test.com", password="ValidPass123"
        )

        background_tasks = BackgroundTasks()
        response = auth_router.register(body, background_tasks, _fake_request())
        user_id = response["user"]["id"]

        # register() queues the real EmailVerificationService.send_verification_email
        # by reference, so only the outbound network call (EmailService) is
        # stubbed here; the token-issuance side effect still runs for real.
        with patch(
            "app.services.email_verification_service.EmailService.send_verification_email"
        ):
            for task in background_tasks.tasks:
                task.func(*task.args, **task.kwargs)

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM email_verifications WHERE user_id = ?",
            (user_id,),
        )
        count = cursor.fetchone()[0]
        connection.close()

        self.assertEqual(count, 1)


class LoginVerificationGateTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

        with patch.object(EmailVerificationService, "send_verification_email"):
            response = auth_router.register(
                auth_router.RegisterRequest(
                    name="User", email="gate@test.com", password="ValidPass123"
                ),
                BackgroundTasks(),
                _fake_request(),
            )

        self.user_id = response["user"]["id"]

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_login_blocked_before_verification(self):
        body = auth_router.LoginRequest(email="gate@test.com", password="ValidPass123")

        with self.assertRaises(HTTPException) as ctx:
            auth_router.login(body, _fake_request())

        self.assertEqual(ctx.exception.status_code, 403)

    def test_login_succeeds_after_verification(self):
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET email_verified = 1 WHERE id = ?", (self.user_id,)
        )
        connection.commit()
        connection.close()

        body = auth_router.LoginRequest(email="gate@test.com", password="ValidPass123")
        response = auth_router.login(body, _fake_request())

        self.assertTrue(response["success"])
        self.assertIn("access_token", response)
        self.assertTrue(response["user"]["email_verified"])

    def test_credits_unreachable_before_verification(self):
        # No JWT can be issued for an unverified user, so the credit-gated
        # /pipeline/start endpoint (which requires get_current_user) is
        # unreachable — proven here by login itself being rejected before
        # any token is ever handed out.
        body = auth_router.LoginRequest(email="gate@test.com", password="ValidPass123")

        with self.assertRaises(HTTPException) as ctx:
            auth_router.login(body, _fake_request())

        self.assertEqual(ctx.exception.status_code, 403)

        user = AuthService.get_user_by_id(self.user_id)
        self.assertGreater(user["credits_remaining"], 0)

    def test_credits_available_after_verification_and_login(self):
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET email_verified = 1 WHERE id = ?", (self.user_id,)
        )
        connection.commit()
        connection.close()

        body = auth_router.LoginRequest(email="gate@test.com", password="ValidPass123")
        response = auth_router.login(body, _fake_request())

        self.assertTrue(response["success"])
        self.assertGreater(response["user"]["credits_remaining"], 0)


class EmailVerificationServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user = AuthService.create_user("User", "svc@test.com", "ValidPass123")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _issue_token(self) -> str:
        # Only the sha256 hash is ever persisted (mirroring password_resets),
        # so the test pins the plaintext by patching secrets.token_urlsafe
        # rather than trying to read it back from the database.
        with patch(
            "app.services.email_verification_service.secrets.token_urlsafe",
            return_value="plaintext-token",
        ), patch(
            "app.services.email_verification_service.EmailService.send_verification_email"
        ):
            EmailVerificationService.send_verification_email(
                self.user["id"], self.user["email"]
            )
        return "plaintext-token"

    def test_verification_succeeds_and_flips_flag(self):
        token = self._issue_token()

        result = EmailVerificationService.verify(token)

        self.assertTrue(result)

        user = AuthService.get_user_by_id(self.user["id"])
        self.assertTrue(user["email_verified"])

    def test_token_cannot_be_reused(self):
        token = self._issue_token()

        self.assertTrue(EmailVerificationService.verify(token))
        self.assertFalse(EmailVerificationService.verify(token))

    def test_expired_token_rejected(self):
        token = self._issue_token()

        # Force the just-issued row into the past, mirroring how
        # test_subscription_expiry.py plants an already-expired state
        # directly rather than waiting out a real clock.
        past = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE email_verifications SET expires_at = ? WHERE user_id = ?",
            (past, self.user["id"]),
        )
        connection.commit()
        connection.close()

        self.assertFalse(EmailVerificationService.verify(token))

        user = AuthService.get_user_by_id(self.user["id"])
        self.assertFalse(user["email_verified"])

    def test_invalid_token_rejected(self):
        self.assertFalse(EmailVerificationService.verify("not-a-real-token"))

    def test_resend_sends_for_unverified_user(self):
        with patch.object(
            EmailVerificationService, "send_verification_email"
        ) as mock_send:
            EmailVerificationService.resend(self.user["email"])

        mock_send.assert_called_once_with(self.user["id"], self.user["email"])

    def test_resend_noop_for_already_verified_user(self):
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET email_verified = 1 WHERE id = ?", (self.user["id"],)
        )
        connection.commit()
        connection.close()

        with patch.object(
            EmailVerificationService, "send_verification_email"
        ) as mock_send:
            EmailVerificationService.resend(self.user["email"])

        mock_send.assert_not_called()

    def test_resend_noop_for_unknown_email(self):
        with patch.object(
            EmailVerificationService, "send_verification_email"
        ) as mock_send:
            EmailVerificationService.resend("nobody@test.com")

        mock_send.assert_not_called()


class ResendVerificationEndpointTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_resend_endpoint_returns_generic_response_regardless_of_outcome(self):
        body = auth_router.ResendVerificationRequest(email="unknown@test.com")

        response = auth_router.resend_verification(
            body, BackgroundTasks(), _fake_request("9.9.9.9")
        )

        self.assertTrue(response["success"])

    def test_resend_endpoint_rate_limited_per_ip(self):
        from app.config.config import settings

        request = _fake_request("10.10.10.10")

        for _ in range(settings.RESEND_VERIFICATION_RATE_LIMIT_MAX_PER_HOUR):
            body = auth_router.ResendVerificationRequest(email="x@test.com")
            response = auth_router.resend_verification(body, BackgroundTasks(), request)
            self.assertTrue(response["success"])

        with self.assertRaises(HTTPException) as ctx:
            auth_router.resend_verification(
                auth_router.ResendVerificationRequest(email="x@test.com"),
                BackgroundTasks(),
                request,
            )

        self.assertEqual(ctx.exception.status_code, 429)


class ExistingUserBackfillTests(unittest.TestCase):
    """
    Simulates a pre-AGC-070 database: a users table created without the
    email_verified column, containing a real pre-existing user, then
    re-runs DatabaseService.initialize() (the same call made on every
    backend startup) to exercise the migration's one-time backfill path.
    """

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        DatabaseService.DB_DIR = Path(self._tmp_dir.name)
        DatabaseService.DB_PATH = Path(self._tmp_dir.name) / "legacy_agc.db"

        import sqlite3

        connection = sqlite3.connect(DatabaseService.DB_PATH)
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                credits_remaining INTEGER NOT NULL DEFAULT 3
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            ("Legacy User", "legacy@test.com", "hash", datetime.utcnow().isoformat()),
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_pre_existing_user_backfilled_to_verified(self):
        DatabaseService.initialize()

        user = AuthService.get_user_by_email("legacy@test.com")

        self.assertTrue(user["email_verified"])

    def test_pre_existing_user_can_still_log_in_after_backfill(self):
        DatabaseService.initialize()

        # Re-hash a known password for the legacy user so login can be
        # exercised end-to-end (the seeded row above used a placeholder hash).
        password_hash = AuthService.hash_password("LegacyPass123")
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (password_hash, "legacy@test.com"),
        )
        connection.commit()
        connection.close()

        body = auth_router.LoginRequest(
            email="legacy@test.com", password="LegacyPass123"
        )
        response = auth_router.login(body, _fake_request())

        self.assertTrue(response["success"])
        self.assertIn("access_token", response)

    def test_rerunning_initialize_does_not_reverify_new_users(self):
        # First startup performs the one-time backfill.
        DatabaseService.initialize()

        with patch.object(EmailVerificationService, "send_verification_email"):
            response = auth_router.register(
                auth_router.RegisterRequest(
                    name="Newcomer", email="newcomer@test.com", password="ValidPass123"
                ),
                BackgroundTasks(),
                _fake_request(),
            )

        self.assertFalse(response["user"]["email_verified"])

        # A later restart re-runs initialize(); the ALTER TABLE now fails
        # with "duplicate column name" so the backfill UPDATE must not
        # run again and flip the new user back to verified.
        DatabaseService.initialize()

        user = AuthService.get_user_by_email("newcomer@test.com")
        self.assertFalse(user["email_verified"])


if __name__ == "__main__":
    unittest.main()
