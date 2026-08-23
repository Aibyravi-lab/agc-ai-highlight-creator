"""VED-MEDIA-001: regression tests for the standalone, production-runnable
diagnostic script (backend/scripts/ved_media_001_storage_diagnostic.py).

This script is meant to be deployed and run directly against production
ahead of (and independently from) the VED-MEDIA-001 cleanup fix, so its
read-only guarantees need their own coverage, separate from the
CleanupService/ProjectService/HistoryService tests:

  1. It never auto-creates a database file that doesn't exist.
  2. Its connection is opened genuinely read-only -- SQLite itself refuses
     a write, not just "the script happens not to issue one."
  3. main() correctly classifies present vs. missing artifacts and returns
     a process exit code reflecting whether anything is broken.
  4. Nothing it does depends on the caller's CWD (relative DB/asset paths
     resolve the same regardless of where the process was launched from).
"""

import importlib.util
import io
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "ved_media_001_storage_diagnostic.py"
)


def _load_diagnostic_module():
    spec = importlib.util.spec_from_file_location(
        "ved_media_001_storage_diagnostic", _SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


diagnostic = _load_diagnostic_module()


class _RestoresCwd(unittest.TestCase):
    """main() intentionally os.chdir()s to backend/ -- restore the real
    CWD afterward so this test doesn't leak state into tests that run
    later in the same pytest session."""

    def setUp(self):
        self._original_cwd = os.getcwd()
        self.addCleanup(os.chdir, self._original_cwd)


class OpenReadonlyConnectionTests(_RestoresCwd):

    def test_refuses_to_open_missing_database(self):

        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "does_not_exist.db"

            with self.assertRaises(SystemExit):
                diagnostic._open_readonly_connection(missing_path)

            self.assertFalse(missing_path.exists())

    def test_readonly_connection_refuses_writes(self):

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "existing.db"

            setup_connection = sqlite3.connect(db_path)
            setup_connection.execute(
                "CREATE TABLE projects (id INTEGER PRIMARY KEY)"
            )
            setup_connection.commit()
            setup_connection.close()

            connection = diagnostic._open_readonly_connection(db_path)

            with self.assertRaises(sqlite3.OperationalError):
                connection.execute(
                    "INSERT INTO projects (id) VALUES (1)"
                )

            connection.close()

    def test_readonly_connection_can_read_existing_data(self):

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "existing.db"

            setup_connection = sqlite3.connect(db_path)
            setup_connection.execute(
                "CREATE TABLE projects (id INTEGER PRIMARY KEY)"
            )
            setup_connection.execute(
                "INSERT INTO projects (id) VALUES (1)"
            )
            setup_connection.commit()
            setup_connection.close()

            connection = diagnostic._open_readonly_connection(db_path)
            rows = connection.execute(
                "SELECT id FROM projects"
            ).fetchall()
            connection.close()

            self.assertEqual(rows, [(1,)])


class MainReportsArtifactStatusTests(_RestoresCwd):

    def _build_projects_db(self, db_path, rows):

        connection = sqlite3.connect(db_path)
        connection.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id TEXT,
                original_video_name TEXT,
                thumbnail_path TEXT,
                horizontal_reel_path TEXT,
                vertical_reel_path TEXT,
                metadata_json_path TEXT,
                status TEXT DEFAULT 'completed',
                created_at TEXT NOT NULL
            )
            """
        )

        for row in rows:
            connection.execute(
                """
                INSERT INTO projects (
                    user_id, job_id, original_video_name,
                    thumbnail_path, horizontal_reel_path,
                    vertical_reel_path, metadata_json_path,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', '2026-01-01')
                """,
                row,
            )

        connection.commit()
        connection.close()

    def test_reports_missing_artifacts_and_nonzero_exit(self):

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            db_path = tmp_dir_path / "agc.db"

            present_thumb = tmp_dir_path / "thumb.jpg"
            present_thumb.write_bytes(b"data")
            present_reel = tmp_dir_path / "reel.mp4"
            present_reel.write_bytes(b"data")

            missing_reel = tmp_dir_path / "gone.mp4"

            self._build_projects_db(
                db_path,
                rows=[
                    (
                        103, "job-ok", "a.mp4",
                        str(present_thumb), str(present_reel),
                        None, None,
                    ),
                    (
                        103, "job-98891-analog", "b.mp4",
                        str(present_thumb), str(missing_reel),
                        None, None,
                    ),
                ],
            )

            with patch.object(
                diagnostic.DatabaseService, "DB_PATH", db_path
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = diagnostic.main()

            self.assertEqual(exit_code, 1)
            output = stdout.getvalue()
            self.assertIn("job-98891-analog", output)
            self.assertIn("MISSING", output)
            self.assertIn("RESULT: 1/2 project(s)", output)

    def test_reports_all_clear_and_zero_exit(self):

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            db_path = tmp_dir_path / "agc.db"

            present_thumb = tmp_dir_path / "thumb.jpg"
            present_thumb.write_bytes(b"data")
            present_reel = tmp_dir_path / "reel.mp4"
            present_reel.write_bytes(b"data")

            self._build_projects_db(
                db_path,
                rows=[
                    (
                        103, "job-ok", "a.mp4",
                        str(present_thumb), str(present_reel),
                        None, None,
                    ),
                ],
            )

            with patch.object(
                diagnostic.DatabaseService, "DB_PATH", db_path
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = diagnostic.main()

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "RESULT: 0/1 project(s)", stdout.getvalue()
            )

    def test_null_asset_paths_are_reported_as_not_applicable_not_missing(self):

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            db_path = tmp_dir_path / "agc.db"

            self._build_projects_db(
                db_path,
                rows=[
                    (
                        103, "job-legacy", "a.mp4",
                        None, None, None, None,
                    ),
                ],
            )

            with patch.object(
                diagnostic.DatabaseService, "DB_PATH", db_path
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = diagnostic.main()

            self.assertEqual(exit_code, 0)
            self.assertIn("n/a", stdout.getvalue())
            self.assertNotIn("MISSING", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
