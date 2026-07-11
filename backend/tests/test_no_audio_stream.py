"""AGC-083 Phase 2: silent-video / no-audio-stream handling.

Production evidence showed a highlight reel with only a video stream
(no audio) reaching Whisper's internal ffmpeg audio extraction, which
crashed with "Output file does not contain any stream" and failed the
job. These tests cover:

  - video_service.has_audio_stream() stream detection
  - AudioService.build_audio_map() falling back to a neutral/silent
    score instead of raising when there is no audio stream
  - WhisperService.transcribe_video() returning a neutral transcription
    instead of invoking ffmpeg audio extraction on a video with no
    audio stream
  - normal audio-containing input behavior is unaffected
"""

import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from app.config.config import settings
from app.services import audio_service, video_service, whisper_service


@pytest.fixture(autouse=True)
def isolated_job_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JOBS_FOLDER", str(tmp_path / "jobs"))
    yield


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["ffprobe"], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# video_service.has_audio_stream()
# ---------------------------------------------------------------------------

def test_has_audio_stream_true_when_audio_stream_present():
    payload = json.dumps({"streams": [{"codec_type": "audio"}]})
    with patch(
        "app.services.video_service.subprocess.run",
        return_value=_completed(stdout=payload),
    ):
        assert video_service.has_audio_stream("video.mp4") is True


def test_has_audio_stream_false_when_no_streams():
    payload = json.dumps({"streams": []})
    with patch(
        "app.services.video_service.subprocess.run",
        return_value=_completed(stdout=payload),
    ):
        assert video_service.has_audio_stream("video.mp4") is False


def test_has_audio_stream_false_on_ffprobe_error():
    with patch(
        "app.services.video_service.subprocess.run",
        return_value=_completed(returncode=1, stderr="No such file"),
    ):
        assert video_service.has_audio_stream("missing.mp4") is False


def test_has_audio_stream_false_on_timeout():
    with patch(
        "app.services.video_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=15),
    ):
        assert video_service.has_audio_stream("video.mp4") is False


# ---------------------------------------------------------------------------
# AudioService.build_audio_map() — no audio stream must not fail the job
# ---------------------------------------------------------------------------

def test_build_audio_map_no_audio_stream_returns_neutral_silent_score():
    with patch(
        "app.services.audio_service.has_audio_stream", return_value=False
    ) as mock_probe, patch(
        "app.services.audio_service.subprocess.run"
    ) as mock_run:
        result = audio_service.AudioService.build_audio_map(
            "silent_video.mp4", job_id="job-no-audio"
        )

    assert result == {"audio_map": {}, "is_silent": True}
    mock_probe.assert_called_once_with("silent_video.mp4")
    # ffmpeg audio extraction must never be attempted on a stream-less input.
    mock_run.assert_not_called()


def test_build_audio_map_with_audio_stream_behaves_normally(tmp_path):
    """Sanity check that detection doesn't disturb the existing
    audio-containing path (real extraction still attempted)."""
    with patch(
        "app.services.audio_service.has_audio_stream", return_value=True
    ), patch(
        "app.services.audio_service.subprocess.run",
        return_value=_completed(),
    ) as mock_run, patch(
        "app.services.audio_service.wave.open",
        side_effect=FileNotFoundError("no wav written by mocked ffmpeg"),
    ):
        # The mocked ffmpeg run doesn't actually write a wav file, so
        # opening it raises — build_audio_map's outer except still
        # guarantees a safe, non-crashing fallback either way.
        result = audio_service.AudioService.build_audio_map(
            "video_with_audio.mp4", job_id="job-with-audio"
        )

    mock_run.assert_called_once()
    assert result["is_silent"] is True


# ---------------------------------------------------------------------------
# WhisperService.transcribe_video() — the actual production crash site
# ---------------------------------------------------------------------------

def test_transcribe_video_no_audio_stream_returns_neutral_transcription():
    with patch(
        "app.services.whisper_service.has_audio_stream", return_value=False
    ), patch(
        "app.services.whisper_service.whisper.audio.load_audio"
    ) as mock_load_audio:
        result = whisper_service.WhisperService.transcribe_video(
            "final_highlight_reel.mp4"
        )

    assert result == {"text": "", "segments": [], "language": None}
    # Must never invoke whisper's internal ffmpeg audio extraction.
    mock_load_audio.assert_not_called()


def test_transcribe_video_no_audio_stream_with_profiler_skips_ffmpeg():
    profiler = MagicMock()

    with patch(
        "app.services.whisper_service.has_audio_stream", return_value=False
    ), patch(
        "app.services.whisper_service.whisper.audio.load_audio"
    ) as mock_load_audio:
        result = whisper_service.WhisperService.transcribe_video(
            "final_highlight_reel.mp4", profiler=profiler
        )

    assert result == {"text": "", "segments": [], "language": None}
    mock_load_audio.assert_not_called()
    profiler.add.assert_not_called()


def test_transcribe_video_with_audio_stream_still_transcribes():
    whisper_service.WhisperService._model = None
    fake_model = MagicMock()
    fake_model.transcribe.return_value = {
        "text": "gg",
        "segments": [{"id": 0}],
        "language": "en",
    }

    with patch(
        "app.services.whisper_service.has_audio_stream", return_value=True
    ), patch.object(
        whisper_service.WhisperService, "get_model", return_value=fake_model
    ):
        result = whisper_service.WhisperService.transcribe_video(
            "video_with_audio.mp4"
        )

    assert result["text"] == "gg"
    fake_model.transcribe.assert_called_once_with("video_with_audio.mp4")
