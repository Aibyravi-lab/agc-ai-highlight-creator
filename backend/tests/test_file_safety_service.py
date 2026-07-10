import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.file_safety_service import FileSafetyService


class FileSafetyServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp_dir.name)

        self.uploads = self.root / "storage" / "uploads"
        self.outputs = self.root / "outputs"
        self.outside = self.root / "outside"

        for folder in (self.uploads, self.outputs, self.outside):
            folder.mkdir(parents=True, exist_ok=True)

        self._patchers = [
            patch.object(settings, "UPLOAD_FOLDER", str(self.uploads)),
            patch.object(settings, "OUTPUT_FOLDER", str(self.outputs)),
            patch.object(settings, "FRAME_FOLDER", str(self.uploads / "__frames")),
            patch.object(settings, "THUMBNAIL_FOLDER", str(self.uploads / "__thumbs")),
            patch.object(settings, "HIGHLIGHT_FOLDER", str(self.uploads / "__highlights")),
            patch.object(settings, "RESULTS_FOLDER", str(self.outputs / "results")),
            patch.object(settings, "JOBS_FOLDER", str(self.uploads / "__jobs")),
        ]

        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()
        self._tmp_dir.cleanup()

    def test_normal_delete_works(self):
        target = self.uploads / "clip.mp4"
        target.write_bytes(b"data")

        result = FileSafetyService.safe_delete_file(target)

        self.assertTrue(result)
        self.assertFalse(target.exists())

    def test_missing_file_does_not_fail(self):
        target = self.uploads / "does_not_exist.mp4"

        result = FileSafetyService.safe_delete_file(target)

        self.assertTrue(result)

    def test_relative_traversal_blocked(self):
        victim = self.outside / "passwd"
        victim.write_text("secret")

        traversal_path = self.uploads / ".." / ".." / "outside" / "passwd"

        result = FileSafetyService.safe_delete_file(traversal_path)

        self.assertFalse(result)
        self.assertTrue(victim.exists())

    def test_absolute_path_outside_storage_blocked(self):
        victim = self.outside / "app.db"
        victim.write_text("db")

        result = FileSafetyService.safe_delete_file(victim)

        self.assertFalse(result)
        self.assertTrue(victim.exists())

    def test_symlink_escape_blocked(self):
        victim = self.outside / "secret.env"
        victim.write_text("SECRET=1")

        link = self.uploads / "link_to_secret"

        try:
            link.symlink_to(victim)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not supported in this environment")

        result = FileSafetyService.safe_delete_file(link)

        self.assertFalse(result)
        self.assertTrue(victim.exists())

    def test_nested_storage_file_deletes_correctly(self):
        nested_dir = self.uploads / "job123" / "frames"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "frame_0001.jpg"
        nested_file.write_bytes(b"frame")

        result = FileSafetyService.safe_delete_file(nested_file)

        self.assertTrue(result)
        self.assertFalse(nested_file.exists())

    def test_storage_root_itself_cannot_be_deleted(self):
        result = FileSafetyService.safe_delete_file(self.uploads)

        self.assertFalse(result)
        self.assertTrue(self.uploads.exists())

    def test_none_path_blocked_without_raising(self):
        result = FileSafetyService.safe_delete_file(None)

        self.assertFalse(result)

    def test_empty_string_path_blocked_without_raising(self):
        result = FileSafetyService.safe_delete_file("")

        self.assertFalse(result)

    def test_whitespace_only_path_blocked_without_raising(self):
        result = FileSafetyService.safe_delete_file("   ")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
