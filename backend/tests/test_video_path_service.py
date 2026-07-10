import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.video_path_service import VideoPathError, VideoPathService


class VideoPathServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp_dir.name)

        self.uploads = self.root / "storage" / "uploads"
        self.outside = self.root / "outside"

        for folder in (self.uploads, self.outside):
            folder.mkdir(parents=True, exist_ok=True)

        self._patcher = patch.object(
            settings, "UPLOAD_FOLDER", str(self.uploads)
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmp_dir.cleanup()

    def _assert_rejected(self, video_path):
        with self.assertRaises(VideoPathError):
            VideoPathService.validate_upload_path(video_path)

    def test_valid_uploaded_video_passes(self):
        video = self.uploads / "abc123_clip.mp4"
        video.write_bytes(b"data")

        result = VideoPathService.validate_upload_path(str(video))

        self.assertEqual(result, str(video.resolve()))

    def test_nested_uploaded_video_passes(self):
        nested = self.uploads / "job1" / "clip.mp4"
        nested.parent.mkdir(parents=True)
        nested.write_bytes(b"data")

        result = VideoPathService.validate_upload_path(str(nested))

        self.assertEqual(result, str(nested.resolve()))

    def test_path_traversal_blocked(self):
        victim = self.outside / "secret.txt"
        victim.write_text("secret")

        self._assert_rejected(
            str(self.uploads / ".." / ".." / "outside" / "secret.txt")
        )

    def test_relative_traversal_string_blocked(self):
        self._assert_rejected("../../secret.txt")

    def test_file_scheme_blocked(self):
        self._assert_rejected("file:///etc/passwd")

    def test_localhost_blocked(self):
        self._assert_rejected("http://localhost")

    def test_loopback_ip_blocked(self):
        self._assert_rejected("http://127.0.0.1")

    def test_private_ip_blocked(self):
        self._assert_rejected("http://10.0.0.5")

    def test_metadata_endpoint_blocked(self):
        self._assert_rejected("http://169.254.169.254")

    def test_absolute_path_outside_storage_blocked(self):
        victim = self.outside / "app.db"
        victim.write_text("db")

        self._assert_rejected(str(victim))

    def test_missing_upload_file_blocked(self):
        self._assert_rejected(str(self.uploads / "does_not_exist.mp4"))

    def test_none_blocked_without_raising_typeerror(self):
        self._assert_rejected(None)

    def test_empty_string_blocked(self):
        self._assert_rejected("")

    def test_whitespace_only_blocked(self):
        self._assert_rejected("   ")

    def test_upload_root_itself_blocked(self):
        self._assert_rejected(str(self.uploads))


if __name__ == "__main__":
    unittest.main()
