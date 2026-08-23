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

        self.owner_id = 1

    def tearDown(self):
        self._patcher.stop()
        self._tmp_dir.cleanup()

    def _assert_rejected(self, video_path, user_id=1):
        with self.assertRaises(VideoPathError):
            VideoPathService.validate_upload_path(video_path, user_id=user_id)

    def test_valid_uploaded_video_passes(self):
        video = self.uploads / f"{self.owner_id}_abc123_clip.mp4"
        video.write_bytes(b"data")

        result = VideoPathService.validate_upload_path(
            str(video), user_id=self.owner_id
        )

        self.assertEqual(result, str(video.resolve()))

    def test_nested_uploaded_video_passes(self):
        nested = (
            self.uploads / "job1" / f"{self.owner_id}_abc123_clip.mp4"
        )
        nested.parent.mkdir(parents=True)
        nested.write_bytes(b"data")

        result = VideoPathService.validate_upload_path(
            str(nested), user_id=self.owner_id
        )

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
        self._assert_rejected(
            str(self.uploads / f"{self.owner_id}_does_not_exist.mp4")
        )

    def test_none_blocked_without_raising_typeerror(self):
        self._assert_rejected(None)

    def test_empty_string_blocked(self):
        self._assert_rejected("")

    def test_whitespace_only_blocked(self):
        self._assert_rejected("   ")

    def test_upload_root_itself_blocked(self):
        self._assert_rejected(str(self.uploads))

    # ── VED-SEC-001: ownership enforcement ──────────────────────────

    def test_other_users_file_rejected(self):
        video = self.uploads / f"{self.owner_id}_abc123_clip.mp4"
        video.write_bytes(b"data")

        with self.assertRaises(VideoPathError):
            VideoPathService.validate_upload_path(str(video), user_id=2)

    def test_owner_can_access_own_file_after_rejection(self):
        # Same file, wrong owner rejected, then the real owner still
        # succeeds — proves the rejection isn't a side effect on the file.
        video = self.uploads / f"{self.owner_id}_abc123_clip.mp4"
        video.write_bytes(b"data")

        with self.assertRaises(VideoPathError):
            VideoPathService.validate_upload_path(str(video), user_id=2)

        result = VideoPathService.validate_upload_path(
            str(video), user_id=self.owner_id
        )
        self.assertEqual(result, str(video.resolve()))

    def test_wrong_owner_and_nonexistent_path_raise_same_message(self):
        # VED-SEC-001: a wrong-owner request must be indistinguishable
        # from a malformed/nonexistent one — no confirmation that another
        # user's file exists.
        video = self.uploads / f"{self.owner_id}_abc123_clip.mp4"
        video.write_bytes(b"data")

        with self.assertRaises(VideoPathError) as wrong_owner_ctx:
            VideoPathService.validate_upload_path(str(video), user_id=2)

        with self.assertRaises(VideoPathError) as bad_path_ctx:
            # Also owned by someone else (not the caller) and also
            # nonexistent -- the ownership check must reject this before
            # ever reaching the is_file() check, exactly as it does for
            # the real-but-not-mine file above.
            VideoPathService.validate_upload_path(
                str(self.uploads / f"{self.owner_id}_totally_fake.mp4"),
                user_id=2
            )

        self.assertEqual(
            str(wrong_owner_ctx.exception), str(bad_path_ctx.exception)
        )

    def test_numeric_prefix_collision_not_exploitable(self):
        # A file named "12_..." must not be claimable by user_id=1 via a
        # naive substring/prefix mix-up.
        video = self.uploads / "12_abcd1234_clip.mp4"
        video.write_bytes(b"data")

        with self.assertRaises(VideoPathError):
            VideoPathService.validate_upload_path(str(video), user_id=1)

        result = VideoPathService.validate_upload_path(
            str(video), user_id=12
        )
        self.assertEqual(result, str(video.resolve()))


if __name__ == "__main__":
    unittest.main()
