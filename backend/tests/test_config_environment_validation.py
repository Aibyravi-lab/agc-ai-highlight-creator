"""Validates the production environment fail-fast guard in app/config/config.py.

That guard (JWT_SECRET_KEY required when ENVIRONMENT=production) has no
existing test coverage. Each case runs in a subprocess with a clean env so
the already-imported app.config.config module in the main test process
isn't affected, and so CONFTEST/other tests never observe ENVIRONMENT set
to "production".
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _import_config_in_subprocess(env_overrides: dict) -> subprocess.CompletedProcess:
    # Run from an empty temp directory (not backend/) so config.py's
    # load_dotenv() cannot pick up a developer's local backend/.env — the
    # guard must depend only on the env vars this test sets, not on
    # whatever secrets happen to exist on the machine running the test.
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(BACKEND_ROOT),
    }
    if sys.platform == "win32":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
    env.update(env_overrides)

    with tempfile.TemporaryDirectory() as tmp_dir:
        return subprocess.run(
            [sys.executable, "-c", "import app.config.config"],
            cwd=tmp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )


class ProductionEnvironmentGuardTests(unittest.TestCase):

    def test_production_without_jwt_secret_fails_fast(self):
        result = _import_config_in_subprocess({"ENVIRONMENT": "production"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JWT_SECRET_KEY is not set", result.stderr)

    def test_production_with_jwt_secret_starts_cleanly(self):
        result = _import_config_in_subprocess(
            {"ENVIRONMENT": "production", "JWT_SECRET_KEY": "a" * 64}
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_development_without_jwt_secret_starts_with_warning(self):
        result = _import_config_in_subprocess({"ENVIRONMENT": "development"})

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("JWT_SECRET_KEY not set", result.stdout)

    def test_default_environment_loads_settings_without_crashing(self):
        result = _import_config_in_subprocess({})

        self.assertEqual(result.returncode, 0, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
