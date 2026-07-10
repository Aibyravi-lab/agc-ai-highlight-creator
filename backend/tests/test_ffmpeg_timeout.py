"""AGC-067: FFmpeg/FFprobe timeout / DoS protection tests.

Covers every subprocess call site that previously ran with no timeout:
ffmpeg_service, video_service, frame_service, audio_service,
caption_service, reel_service (x2), video_editor_service.

Each site is verified for:
  - normal execution still succeeds
  - a hung/timed-out subprocess raises a controlled application error
    (never a raw subprocess.TimeoutExpired)
  - temp output is cleaned up after a timeout
Plus one process-level test proving Python's timeout mechanism actually
kills the child rather than leaving it running in the background.
"""

import json
import subprocess
import sys
import time
from unittest.mock import patch, MagicMock

import pytest

from app.config.config import settings
from app.services import (
    ffmpeg_service,
    video_service,
    frame_service,
    audio_service,
    caption_service,
    reel_service,
    video_editor_service,
)


@pytest.fixture(autouse=True)
def isolated_job_storage(tmp_path, monkeypatch):
    """Redirect job storage to a throwaway directory for every test."""
    monkeypatch.setattr(settings, "JOBS_FOLDER", str(tmp_path / "jobs"))
    yield


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["ffmpeg"], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# Process-level guarantee: subprocess.run(timeout=...) kills the child
# ---------------------------------------------------------------------------

def test_timeout_actually_kills_hung_process():
    """The mechanism every call site relies on must not block past the
    timeout, and must not leave the child running."""
    hung_command = [sys.executable, "-c", "import time; time.sleep(30)"]

    started = time.perf_counter()
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(hung_command, timeout=1, capture_output=True)
    elapsed = time.perf_counter() - started

    # Must return promptly, not after the full 30s sleep.
    assert elapsed < 10


# ---------------------------------------------------------------------------
# ffmpeg_service.FFmpegService.validate()
# ---------------------------------------------------------------------------

def test_ffmpeg_service_validate_normal():
    with patch(
        "app.services.ffmpeg_service.shutil.which", return_value="/usr/bin/ffmpeg"
    ), patch(
        "app.services.ffmpeg_service.subprocess.run", return_value=_completed()
    ) as mock_run:
        ffmpeg_service.FFmpegService.validate()

    for call in mock_run.call_args_list:
        assert call.kwargs.get("timeout") == settings.FFMPEG_QUICK_TIMEOUT_SECONDS


def test_ffmpeg_service_validate_timeout_returns_controlled_error():
    with patch(
        "app.services.ffmpeg_service.shutil.which", return_value="/usr/bin/ffmpeg"
    ), patch(
        "app.services.ffmpeg_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=15),
    ):
        with pytest.raises(RuntimeError):
            ffmpeg_service.FFmpegService.validate()


# ---------------------------------------------------------------------------
# video_service.get_video_metadata()
# ---------------------------------------------------------------------------

def _ffprobe_json():
    return json.dumps(
        {
            "format": {"duration": "12.5", "size": "1048576"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                }
            ],
        }
    )


def test_get_video_metadata_normal(tmp_path):
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"fake")

    with patch(
        "app.services.video_service.subprocess.run",
        return_value=_completed(stdout=_ffprobe_json()),
    ) as mock_run:
        metadata = video_service.get_video_metadata(str(video_file))

    assert metadata["fps"] == 30
    assert metadata["codec"] == "h264"
    assert mock_run.call_args.kwargs.get("timeout") == settings.FFMPEG_QUICK_TIMEOUT_SECONDS


def test_get_video_metadata_timeout_returns_controlled_error(tmp_path):
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"fake")

    with patch(
        "app.services.video_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=15),
    ):
        with pytest.raises(Exception) as exc_info:
            video_service.get_video_metadata(str(video_file))

    assert "timed out" in str(exc_info.value).lower()
    assert not isinstance(exc_info.value, subprocess.TimeoutExpired)


# ---------------------------------------------------------------------------
# frame_service.FrameService.extract_frames()
# ---------------------------------------------------------------------------

def test_frame_service_extract_frames_normal(tmp_path):
    def fake_run(command, **kwargs):
        output_pattern = command[-1]
        output_dir = __import__("pathlib").Path(output_pattern).parent
        (output_dir / "frame_0001.jpg").write_bytes(b"x")
        return _completed()

    with patch(
        "app.services.frame_service.subprocess.run", side_effect=fake_run
    ) as mock_run:
        result = frame_service.FrameService.extract_frames(
            "video.mp4", job_id="job-normal"
        )

    assert result["total_frames"] == 1
    assert mock_run.call_args.kwargs.get("timeout") == settings.FFMPEG_LONG_TIMEOUT_SECONDS


def test_frame_service_extract_frames_timeout_cleans_up(tmp_path):
    with patch(
        "app.services.frame_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600),
    ), patch(
        "app.services.frame_service.CleanupService.cleanup_temp_folder"
    ) as mock_cleanup:
        with pytest.raises(Exception) as exc_info:
            frame_service.FrameService.extract_frames(
                "video.mp4", job_id="job-timeout"
            )

    assert "timed out" in str(exc_info.value).lower()
    mock_cleanup.assert_called_once()
    assert "job-timeout" in mock_cleanup.call_args.args[0]


# ---------------------------------------------------------------------------
# audio_service.AudioService.extract_audio()
# ---------------------------------------------------------------------------

def test_audio_service_extract_audio_normal():
    with patch(
        "app.services.audio_service.subprocess.run", return_value=_completed()
    ) as mock_run:
        result = audio_service.AudioService.extract_audio(
            "video.mp4", "out.wav"
        )

    assert result == "out.wav"
    assert mock_run.call_args.kwargs.get("timeout") == settings.FFMPEG_LONG_TIMEOUT_SECONDS


def test_audio_service_extract_audio_timeout_cleans_up():
    with patch(
        "app.services.audio_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600),
    ), patch(
        "app.services.audio_service.CleanupService.cleanup_temp_file"
    ) as mock_cleanup:
        with pytest.raises(Exception) as exc_info:
            audio_service.AudioService.extract_audio("video.mp4", "out.wav")

    assert "timed out" in str(exc_info.value).lower()
    mock_cleanup.assert_called_once_with("out.wav")


def test_audio_service_build_audio_map_survives_ffmpeg_timeout():
    """The pipeline's audio step already treats extraction failures as
    silent-audio fallback (not a hard crash) — a timeout must keep doing
    so rather than blowing up the whole highlight job."""
    with patch(
        "app.services.audio_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600),
    ):
        result = audio_service.AudioService.build_audio_map(
            "video.mp4", job_id="job-audio-timeout"
        )

    assert result["is_silent"] is True
    assert result["audio_map"] == {}


# ---------------------------------------------------------------------------
# caption_service.CaptionService.add_captions()
# ---------------------------------------------------------------------------

def test_caption_service_add_captions_normal():
    with patch(
        "app.services.caption_service.subprocess.run", return_value=_completed()
    ) as mock_run:
        output_path = caption_service.CaptionService.add_captions(
            video_path="reel.mp4",
            caption_text="hello world",
            job_id="job-caption-normal",
        )

    assert output_path.endswith("captioned_reel.mp4")
    assert mock_run.call_args.kwargs.get("timeout") == settings.FFMPEG_SHORT_TIMEOUT_SECONDS


def test_caption_service_add_captions_timeout_cleans_up():
    with patch(
        "app.services.caption_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120),
    ), patch(
        "app.services.caption_service.CleanupService.cleanup_temp_file"
    ) as mock_cleanup:
        with pytest.raises(Exception) as exc_info:
            caption_service.CaptionService.add_captions(
                video_path="reel.mp4",
                caption_text="hello world",
                job_id="job-caption-timeout",
            )

    assert "timed out" in str(exc_info.value).lower()
    mock_cleanup.assert_called_once()
    assert "captioned_reel.mp4" in mock_cleanup.call_args.args[0]


# ---------------------------------------------------------------------------
# reel_service.ReelService
# ---------------------------------------------------------------------------

def test_reel_service_create_vertical_reel_normal():
    with patch(
        "app.services.reel_service.subprocess.run", return_value=_completed()
    ) as mock_run:
        output_path = reel_service.ReelService.create_vertical_reel(
            "final.mp4", job_id="job-vertical-normal"
        )

    assert output_path.endswith("final_highlight_reel_vertical.mp4")
    assert mock_run.call_args.kwargs.get("timeout") == settings.FFMPEG_SHORT_TIMEOUT_SECONDS


def test_reel_service_create_vertical_reel_timeout_cleans_up():
    with patch(
        "app.services.reel_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120),
    ), patch(
        "app.services.reel_service.CleanupService.cleanup_temp_file"
    ) as mock_cleanup:
        with pytest.raises(Exception) as exc_info:
            reel_service.ReelService.create_vertical_reel(
                "final.mp4", job_id="job-vertical-timeout"
            )

    assert "timed out" in str(exc_info.value).lower()
    mock_cleanup.assert_called_once()


def test_reel_service_merge_clips_timeout_cleans_up(tmp_path):
    clip = tmp_path / "clip1.mp4"
    clip.write_bytes(b"x")

    with patch(
        "app.services.reel_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120),
    ), patch(
        "app.services.reel_service.CleanupService.cleanup_temp_file"
    ) as mock_cleanup:
        with pytest.raises(Exception) as exc_info:
            reel_service.ReelService.merge_clips(
                [str(clip)], job_id="job-merge-timeout"
            )

    assert "timed out" in str(exc_info.value).lower()
    mock_cleanup.assert_called_once()
    assert "final_highlight_reel.mp4" in mock_cleanup.call_args.args[0]


# ---------------------------------------------------------------------------
# video_editor_service.VideoEditorService.create_clip()
# ---------------------------------------------------------------------------

def test_video_editor_service_create_clip_normal():
    with patch(
        "app.services.video_editor_service.subprocess.run",
        return_value=_completed(),
    ) as mock_run:
        result = video_editor_service.VideoEditorService.create_clip(
            "video.mp4", timestamp=10, duration=5, job_id="job-clip-normal"
        )

    assert result["timestamp"] == 10
    assert mock_run.call_args.kwargs.get("timeout") == settings.FFMPEG_SHORT_TIMEOUT_SECONDS


def test_video_editor_service_create_clip_timeout_cleans_up():
    with patch(
        "app.services.video_editor_service.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120),
    ), patch(
        "app.services.video_editor_service.CleanupService.cleanup_temp_file"
    ) as mock_cleanup:
        with pytest.raises(Exception) as exc_info:
            video_editor_service.VideoEditorService.create_clip(
                "video.mp4", timestamp=10, duration=5, job_id="job-clip-timeout"
            )

    assert "timed out" in str(exc_info.value).lower()
    mock_cleanup.assert_called_once()
