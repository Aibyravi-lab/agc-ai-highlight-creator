"""VED-P1-003: AI worker throughput fix.

CTO audit hypothesis: AI processing (CLIP + Whisper inference) appeared
serialized regardless of MAX_CONCURRENT_JOBS. Root cause was a global
`threading.Lock` in each of ClipService and WhisperService wrapping every
inference call, added earlier to stop concurrent forward passes on a
*shared* model instance from racing on internal buffers.

The fix gives each ThreadPoolExecutor worker thread its own model/processor
instance (via `threading.local()`) instead of sharing one guarded by a lock.
Since no thread ever touches another thread's instance, there is no shared
mutable state left to race on. These tests guard:

  - the lock attributes are gone (regression against reintroducing the
    bottleneck)
  - each thread lazily gets its own, independent model/processor instance
  - a thread reuses its own instance across repeated calls (no reload per
    call)
  - concurrent inference from multiple threads never touches another
    thread's instance

Model loading is mocked throughout — no real CLIP/Whisper weights are
downloaded or run, matching this suite's existing convention of mocking
heavy external dependencies (see test_no_audio_stream.py).
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from app.services import clip_service, whisper_service


@pytest.fixture(autouse=True)
def isolated_thread_locals():
    """Each test gets fresh thread-local storage, and the main test thread's
    slot is cleared afterwards so tests never see another test's mock model.
    """
    clip_service.ClipService._thread_local = threading.local()
    whisper_service.WhisperService._thread_local = threading.local()
    yield
    clip_service.ClipService._thread_local = threading.local()
    whisper_service.WhisperService._thread_local = threading.local()


# ---------------------------------------------------------------------------
# Regression: the global locks that caused full serialization must stay gone
# ---------------------------------------------------------------------------

def test_clip_service_has_no_global_inference_lock():
    assert not hasattr(clip_service.ClipService, "_inference_lock")


def test_whisper_service_has_no_global_lock():
    assert not hasattr(whisper_service.WhisperService, "_lock")


# ---------------------------------------------------------------------------
# ClipService — per-thread model/processor isolation
# ---------------------------------------------------------------------------

def test_clip_service_different_threads_get_different_model_instances():
    with patch.object(
        clip_service, "CLIPModel"
    ) as mock_model_cls, patch.object(
        clip_service, "CLIPProcessor"
    ) as mock_processor_cls:

        mock_model_cls.from_pretrained.side_effect = (
            lambda *a, **k: MagicMock()
        )
        mock_processor_cls.from_pretrained.side_effect = (
            lambda *a, **k: MagicMock()
        )

        seen: dict = {}

        def worker(name: str):
            model, processor = (
                clip_service.ClipService._get_model_and_processor()
            )
            seen[name] = (model, processor)

        threads = [
            threading.Thread(target=worker, args=(f"t{i}",))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        models = [m for m, _ in seen.values()]
        processors = [p for _, p in seen.values()]

        assert len(set(id(m) for m in models)) == len(models)
        assert len(set(id(p) for p in processors)) == len(processors)
        assert mock_model_cls.from_pretrained.call_count == len(threads)


def test_clip_service_same_thread_reuses_its_own_instance():
    with patch.object(
        clip_service, "CLIPModel"
    ) as mock_model_cls, patch.object(
        clip_service, "CLIPProcessor"
    ) as mock_processor_cls:

        mock_model_cls.from_pretrained.side_effect = (
            lambda *a, **k: MagicMock()
        )
        mock_processor_cls.from_pretrained.side_effect = (
            lambda *a, **k: MagicMock()
        )

        model_1, processor_1 = (
            clip_service.ClipService._get_model_and_processor()
        )
        model_2, processor_2 = (
            clip_service.ClipService._get_model_and_processor()
        )

        assert model_1 is model_2
        assert processor_1 is processor_2
        assert mock_model_cls.from_pretrained.call_count == 1


# ---------------------------------------------------------------------------
# WhisperService — per-thread model isolation
# ---------------------------------------------------------------------------

def test_whisper_service_different_threads_get_different_model_instances():
    with patch.object(whisper_service, "whisper") as mock_whisper:
        mock_whisper.load_model.side_effect = lambda *a, **k: MagicMock()

        seen: dict = {}

        def worker(name: str):
            seen[name] = whisper_service.WhisperService.get_model()

        threads = [
            threading.Thread(target=worker, args=(f"t{i}",))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(id(m) for m in seen.values())) == len(seen)
        assert mock_whisper.load_model.call_count == len(threads)


def test_whisper_service_same_thread_reuses_its_own_instance():
    with patch.object(whisper_service, "whisper") as mock_whisper:
        mock_whisper.load_model.side_effect = lambda *a, **k: MagicMock()

        model_1 = whisper_service.WhisperService.get_model()
        model_2 = whisper_service.WhisperService.get_model()

        assert model_1 is model_2
        assert mock_whisper.load_model.call_count == 1


# ---------------------------------------------------------------------------
# Concurrency: many threads calling in at once never cross-contaminate
# ---------------------------------------------------------------------------

def test_clip_service_concurrent_analyze_frame_stays_isolated_per_thread(
    tmp_path,
):
    import torch
    from PIL import Image

    image_path = tmp_path / "frame.jpg"
    Image.new("RGB", (4, 4)).save(image_path)

    def processor_call(text=None, images=None, **_kwargs):
        # Round-trips how many prompts were embedded so the fake model
        # below can return a shape that actually matches, without either
        # side needing to know the real prompt list length.
        return {"__num_rows__": len(text) if text is not None else 1}

    def make_fake_processor():
        return MagicMock(side_effect=processor_call)

    def make_fake_model():
        fake_model = MagicMock()

        def text_features(**kwargs):
            out = MagicMock()
            out.pooler_output = torch.ones((kwargs["__num_rows__"], 4))
            return out

        def image_features(**kwargs):
            out = MagicMock()
            out.pooler_output = torch.ones((kwargs["__num_rows__"], 4))
            return out

        fake_model.get_text_features.side_effect = text_features
        fake_model.get_image_features.side_effect = image_features
        fake_model.logit_scale.exp.return_value = torch.tensor(1.0)
        return fake_model

    with patch.object(
        clip_service, "CLIPModel"
    ) as mock_model_cls, patch.object(
        clip_service, "CLIPProcessor"
    ) as mock_processor_cls:

        mock_model_cls.from_pretrained.side_effect = (
            lambda *a, **k: make_fake_model()
        )
        mock_processor_cls.from_pretrained.side_effect = (
            lambda *a, **k: make_fake_processor()
        )

        errors: list = []

        def worker():
            try:
                for _ in range(5):
                    clip_service.ClipService.analyze_frame(str(image_path))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # One model+processor pair loaded per worker thread, never shared.
        assert mock_model_cls.from_pretrained.call_count == len(threads)
