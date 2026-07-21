"""
VED-INC-001: test_systemd_unit_path.py guards the *text* of the systemd
unit's Environment=PATH=. This test guards the thing that actually broke
production -- real PATH resolution in the process's own environment -- by
calling the exact same shutil.which() lookups, and the exact same
FFmpegService.validate() startup check, that raised
"RuntimeError: FFmpeg not installed or not available in PATH" when PATH
was venv/bin only. If ffmpeg/ffprobe ever again become unresolvable in the
environment this suite runs in, this test fails instead of that only
surfacing after a production deploy.
"""

import shutil
import unittest

from app.services.ffmpeg_service import FFmpegService


class FFmpegPathResolutionTests(unittest.TestCase):

    def test_ffmpeg_and_ffprobe_are_resolvable_and_validate_passes(self):
        self.assertIsNotNone(
            shutil.which("ffmpeg"),
            "ffmpeg is not resolvable via PATH in this environment -- this "
            "is the exact condition that made FFmpegService.validate() "
            "raise RuntimeError and crash backend startup in production.",
        )
        self.assertIsNotNone(
            shutil.which("ffprobe"),
            "ffprobe is not resolvable via PATH in this environment -- "
            "same failure mode as the ffmpeg check above.",
        )

        # The real startup call (app/main.py) -- must not raise.
        FFmpegService.validate()


if __name__ == "__main__":
    unittest.main()
