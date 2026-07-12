"""AGC-084: MaintenanceService — live, uncached file-existence check that
drives maintenance-mode enforcement across /upload, /pipeline/start, and
the public /maintenance-status endpoint.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.maintenance_service import MaintenanceService


class MaintenanceServiceTests(unittest.TestCase):

    def test_flag_absent_is_not_maintenance_mode(self):
        with patch.object(
            settings, "MAINTENANCE_FLAG_PATH", "does/not/exist/maintenance.flag"
        ):
            self.assertFalse(MaintenanceService.is_maintenance_mode())

    def test_flag_present_is_maintenance_mode(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            flag_path = Path(tmp_dir) / "maintenance.flag"
            flag_path.touch()

            with patch.object(
                settings, "MAINTENANCE_FLAG_PATH", str(flag_path)
            ):
                self.assertTrue(MaintenanceService.is_maintenance_mode())

    def test_missing_parent_directory_reads_safely_as_false(self):
        with patch.object(
            settings,
            "MAINTENANCE_FLAG_PATH",
            "totally/nonexistent/parent/dir/maintenance.flag",
        ):
            # Must not raise — a missing parent directory is a normal,
            # expected "maintenance is off" state, not an error.
            self.assertFalse(MaintenanceService.is_maintenance_mode())

    def test_filesystem_error_reads_safely_as_false(self):
        with patch.object(
            settings, "MAINTENANCE_FLAG_PATH", "irrelevant.flag"
        ), patch(
            "app.services.maintenance_service.Path.exists",
            side_effect=OSError("simulated filesystem error"),
        ):
            self.assertFalse(MaintenanceService.is_maintenance_mode())

    def test_removing_flag_after_creation_turns_maintenance_off(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            flag_path = Path(tmp_dir) / "maintenance.flag"

            with patch.object(
                settings, "MAINTENANCE_FLAG_PATH", str(flag_path)
            ):
                self.assertFalse(MaintenanceService.is_maintenance_mode())

                flag_path.touch()
                self.assertTrue(MaintenanceService.is_maintenance_mode())

                flag_path.unlink()
                self.assertFalse(MaintenanceService.is_maintenance_mode())


if __name__ == "__main__":
    unittest.main()
