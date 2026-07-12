"""AGC-082.2: absolute noise-floor classification gate.

Production evidence showed a technically-present but practically inaudible
audio stream (ffmpeg volumedetect: mean_volume -90.3 dB, max_volume -76.3 dB)
being scored as audio_score=1.0 and surfaced as "Audio spike", because
AudioService.build_audio_map() normalized purely relative to the loudest
sample in the track (peak / max_amplitude) — any nonzero track therefore
guarantees its loudest instant a score of 1.0, no matter how quiet.

These tests cover the new absolute dBFS gate added ahead of that relative
normalization:

  - no-audio-stream behavior is unchanged (AGC-083 contract)
  - bit-exact-zero behavior is unchanged
  - low nonzero, near-silent PCM (matching the production -76.3 dBFS
    evidence) is now classified silent, before normalization runs
  - a near-silent track can no longer produce a meaningful (nonzero) audio
    score through relative normalization
  - clearly meaningful audio remains non-silent and keeps its existing
    relative-normalization scoring behavior
"""

import subprocess
import wave
from unittest.mock import patch

import numpy as np
import pytest

from app.config.config import settings
from app.services import audio_service

FRAME_RATE = 16000


@pytest.fixture(autouse=True)
def isolated_job_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "JOBS_FOLDER", str(tmp_path / "jobs"))
    yield


def _write_wav(path: str, samples: np.ndarray, frame_rate: int = FRAME_RATE) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(frame_rate)
        wf.writeframes(samples.astype(np.int16).tobytes())


def _fake_ffmpeg_extraction(samples: np.ndarray, frame_rate: int = FRAME_RATE):
    """subprocess.run replacement that writes `samples` as the "extracted"
    wav instead of actually invoking ffmpeg, so build_audio_map's numpy/wave
    reading logic runs against genuine PCM data."""

    def _run(command, **kwargs):
        output_path = command[-1]
        _write_wav(output_path, samples, frame_rate)
        return subprocess.CompletedProcess(
            args=command, returncode=0, stdout="", stderr=""
        )

    return _run


def test_no_audio_stream_remains_silent_with_empty_map():
    with patch(
        "app.services.audio_service.has_audio_stream", return_value=False
    ):
        result = audio_service.AudioService.build_audio_map(
            "silent_video.mp4", job_id="job-no-stream"
        )

    assert result == {"audio_map": {}, "is_silent": True}


def test_bit_exact_zero_audio_remains_silent_with_empty_map():
    samples = np.zeros(FRAME_RATE * 2, dtype=np.int16)

    with patch(
        "app.services.audio_service.has_audio_stream", return_value=True
    ), patch(
        "app.services.audio_service.subprocess.run",
        side_effect=_fake_ffmpeg_extraction(samples),
    ):
        result = audio_service.AudioService.build_audio_map(
            "zero_audio_video.mp4", job_id="job-zero-audio"
        )

    assert result == {"audio_map": {}, "is_silent": True}


def test_near_silent_noise_floor_is_classified_silent():
    """Peak amplitude 5 out of 32767 full scale is ~-76.3 dBFS — matching
    the production evidence — and must be gated as silent before the
    relative peak/max_amplitude normalization ever runs."""
    rng = np.random.default_rng(seed=42)
    samples = rng.integers(-5, 6, size=FRAME_RATE * 2).astype(np.int16)

    max_volume_dbfs = 20 * np.log10(5 / audio_service.PCM_INT16_FULL_SCALE)
    assert max_volume_dbfs == pytest.approx(-76.3, abs=0.1)

    with patch(
        "app.services.audio_service.has_audio_stream", return_value=True
    ), patch(
        "app.services.audio_service.subprocess.run",
        side_effect=_fake_ffmpeg_extraction(samples),
    ):
        result = audio_service.AudioService.build_audio_map(
            "near_silent_video.mp4", job_id="job-near-silent"
        )

    assert result == {"audio_map": {}, "is_silent": True}


def test_near_silent_audio_cannot_produce_a_nonzero_audio_score():
    rng = np.random.default_rng(seed=7)
    samples = rng.integers(-5, 6, size=FRAME_RATE * 3).astype(np.int16)

    with patch(
        "app.services.audio_service.has_audio_stream", return_value=True
    ), patch(
        "app.services.audio_service.subprocess.run",
        side_effect=_fake_ffmpeg_extraction(samples),
    ):
        result = audio_service.AudioService.build_audio_map(
            "near_silent_video.mp4", job_id="job-near-silent-score"
        )

    score = audio_service.AudioService.get_windowed_audio_score(
        audio_map=result["audio_map"], timestamp=1
    )

    assert score == 0.0


def test_clearly_meaningful_audio_remains_non_silent_and_normalizes_as_before():
    """One quiet-but-real second (peak 1000, ~-30 dBFS) and one loud second
    (peak 20000, ~-4.3 dBFS) — both well above the -60 dBFS gate. Confirms
    normal gameplay audio is unaffected and existing relative normalization
    (peak / max_amplitude) still produces the expected per-second scores."""
    quiet_second = np.full(FRAME_RATE, 1000, dtype=np.int16)
    loud_second = np.full(FRAME_RATE, 20000, dtype=np.int16)
    samples = np.concatenate([quiet_second, loud_second])

    with patch(
        "app.services.audio_service.has_audio_stream", return_value=True
    ), patch(
        "app.services.audio_service.subprocess.run",
        side_effect=_fake_ffmpeg_extraction(samples),
    ):
        result = audio_service.AudioService.build_audio_map(
            "normal_audio_video.mp4", job_id="job-normal-audio"
        )

    assert result["is_silent"] is False
    assert result["audio_map"][0] == pytest.approx(1000 / 20000, abs=0.001)
    assert result["audio_map"][1] == pytest.approx(1.0, abs=0.001)
