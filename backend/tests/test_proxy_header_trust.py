"""
VED-SEC-001: proves the app resolves the real client IP through the
nginx -> Uvicorn proxy-header boundary, exactly as configured in
backend/scripts/agc-backend.service (--proxy-headers
--forwarded-allow-ips=127.0.0.1).

test_rate_limiting.py already proves RateLimitService/the auth router key
correctly *once request.client.host is correct* (it injects request.client
directly via a SimpleNamespace fake). This file closes the layer those
tests skip: it wraps the real ASGI app in uvicorn's own
ProxyHeadersMiddleware -- the same middleware Uvicorn applies automatically
when started with --proxy-headers -- and drives it through TestClient with
an explicit simulated TCP peer, so the X-Forwarded-For trust decision
itself is under test, not assumed.
"""

import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config.config import settings
from app.routers import auth as auth_router
from app.services.database_service import DatabaseService

# Matches nginx/agc.conf: nginx always connects to Uvicorn from the loopback
# address and sets X-Forwarded-For to the real client. This is exactly what
# --forwarded-allow-ips=127.0.0.1 (backend/scripts/agc-backend.service)
# tells Uvicorn to trust.
_TRUSTED_PROXY_PEER = ("127.0.0.1", 54321)

# Simulates a request that reaches Uvicorn without going through nginx
# (e.g. a misconfiguration or a direct connection) -- its X-Forwarded-For
# must NOT be trusted.
_UNTRUSTED_PEER = ("203.0.113.9", 54321)


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _client(peer):
    """A TestClient wired exactly like production: real auth router,
    wrapped in the same ProxyHeadersMiddleware Uvicorn installs when run
    with --proxy-headers --forwarded-allow-ips=127.0.0.1, with `peer` as
    the simulated raw TCP connection address."""
    app = FastAPI()
    app.include_router(auth_router.router)
    wrapped = ProxyHeadersMiddleware(app, trusted_hosts="127.0.0.1")
    return TestClient(wrapped, client=peer)


def _bad_login(client, forwarded_for=None):
    headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
    return client.post(
        "/auth/login",
        json={"email": "nobody@test.com", "password": "wrong-password"},
        headers=headers,
    )


class ProxyHeaderTrustTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_trusted_proxy_forwarded_ips_get_independent_rate_limit_buckets(self):
        client = _client(_TRUSTED_PROXY_PEER)
        limit = settings.LOGIN_RATE_LIMIT_MAX_PER_MINUTE

        for _ in range(limit):
            response = _bad_login(client, forwarded_for="198.51.100.11")
            self.assertEqual(response.status_code, 401)

        # This external client's budget is now exhausted.
        response = _bad_login(client, forwarded_for="198.51.100.11")
        self.assertEqual(response.status_code, 429)

        # A different external client, forwarded through the same trusted
        # nginx peer, must have its own untouched budget -- this is the
        # exact property that was broken when request.client.host resolved
        # to nginx's own loopback address for every visitor.
        response = _bad_login(client, forwarded_for="198.51.100.22")
        self.assertEqual(response.status_code, 401)

    def test_untrusted_peer_cannot_spoof_forwarded_for_to_bypass_rate_limit(self):
        client = _client(_UNTRUSTED_PEER)
        limit = settings.LOGIN_RATE_LIMIT_MAX_PER_MINUTE

        for _ in range(limit):
            # A different forged X-Forwarded-For on every request.
            response = _bad_login(client, forwarded_for=f"1.2.3.{_}")
            self.assertEqual(response.status_code, 401)

        # Because the peer isn't the trusted proxy, every one of the
        # requests above must have been keyed on the real (untrusted) peer
        # address, not the forged header -- so the budget is exhausted
        # despite each request claiming a fresh source IP.
        response = _bad_login(client, forwarded_for="9.9.9.9")
        self.assertEqual(response.status_code, 429)

    def test_systemd_unit_explicitly_trusts_only_the_nginx_loopback_peer(self):
        unit_path = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "agc-backend.service"
        )
        contents = unit_path.read_text()

        exec_start_lines = [
            line for line in contents.splitlines()
            if line.strip().startswith("ExecStart=")
        ]
        self.assertEqual(len(exec_start_lines), 1)
        exec_start = exec_start_lines[0]

        self.assertIn("--proxy-headers", exec_start)
        self.assertIn("--forwarded-allow-ips=127.0.0.1", exec_start)


if __name__ == "__main__":
    unittest.main()
