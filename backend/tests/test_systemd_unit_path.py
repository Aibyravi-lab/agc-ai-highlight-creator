"""
VED-SEC-001 follow-up: production discovered that the systemd unit's
Environment=PATH=... (set since AGC-045.2, unrelated to the VED-SEC-001
proxy-headers change) contained only the venv's own bin directory.
FFmpegService.validate() and every ffmpeg/ffprobe/git subprocess call in
this codebase resolve their executable by bare name (shutil.which() /
PATH lookup), never an absolute path, and none of those binaries live in
the venv -- so a venv-only PATH made the backend fail to start.

This guards two properties statically, since PATH resolution itself is an
OS/systemd-level concern a Python test can't exercise directly:
  1. The venv's own bin directory is still first on PATH (so any bare
     python/pip lookup keeps resolving to the venv, unchanged from before).
  2. The standard system directories where ffmpeg/ffprobe/git are actually
     installed (docs/deploy.md, docs/VPS_REBUILD.md: `apt install ffmpeg
     git`) are present on PATH.
"""

import unittest
from pathlib import Path


class SystemdUnitPathTests(unittest.TestCase):

    def setUp(self):
        unit_path = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "agc-backend.service"
        )
        self.contents = unit_path.read_text()

        path_lines = [
            line for line in self.contents.splitlines()
            if line.strip().startswith("Environment=PATH=")
        ]
        self.assertEqual(
            len(path_lines), 1,
            "expected exactly one Environment=PATH= directive",
        )
        self.path_value = path_lines[0].split("Environment=PATH=", 1)[1]
        self.path_entries = self.path_value.split(":")

    def test_venv_bin_is_still_first_on_path(self):
        self.assertEqual(
            self.path_entries[0],
            "/home/agc/agc-ai-highlight-creator/venv/bin",
            "venv/bin must stay first so bare python/pip lookups are "
            "unaffected by this fix",
        )

    def test_system_binary_directories_are_present(self):
        for required_dir in ("/usr/local/bin", "/usr/bin", "/bin"):
            self.assertIn(
                required_dir,
                self.path_entries,
                f"{required_dir} must be on PATH for ffmpeg/ffprobe/git "
                "(apt-installed, per docs/deploy.md) to be resolvable via "
                "shutil.which()",
            )


if __name__ == "__main__":
    unittest.main()
