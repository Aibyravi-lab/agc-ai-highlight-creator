"""VED-P1-018-A: remove eager BLIP model loading from the import path.

VisionService used to load BLIP (processor + model) as class attributes,
evaluated the instant `app.services.vision_service` was imported -- which
happens during `app.routers.vision` import, before FastAPI is constructed
or the socket is bound (see P1-018 root-cause report). ClipService and
WhisperService already solved this for CLIP/Whisper via a thread-local
lazy-load pattern (VED-P1-003); this brings VisionService in line with
that established pattern.

These tests guard:
  - importing/reloading the module never calls BLIP's from_pretrained()
  - the first real call lazily loads exactly once
  - a thread reuses its own instance across repeated calls (no reload)
  - concurrent threads never share an instance
  - analyze_frame's public return shape is unchanged

`from_pretrained` is patched directly on the already-resolved
BlipProcessor/BlipForConditionalGeneration class objects (rather than
reassigning the module-level names) because transformers exposes these
classes through a lazy-loading module proxy (`_LazyModule`) whose
`__getattr__` re-resolves on every `from transformers import X`, which
silently discards a name-level patch across `importlib.reload()`.
Patching the classmethod directly on the class object is unaffected by
that, since reload re-imports a reference to the same class object.
"""

import importlib
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.services import vision_service


@pytest.fixture(autouse=True)
def isolated_thread_local():
    """Each test gets fresh thread-local storage."""
    vision_service.VisionService._thread_local = threading.local()
    yield
    vision_service.VisionService._thread_local = threading.local()


# ---------------------------------------------------------------------------
# Regression: importing/reloading the module must not load BLIP
# ---------------------------------------------------------------------------

def test_importing_vision_service_does_not_load_blip_model():
    with patch.object(
        vision_service.BlipProcessor, "from_pretrained"
    ) as mock_processor_load, patch.object(
        vision_service.BlipForConditionalGeneration, "from_pretrained"
    ) as mock_model_load:

        importlib.reload(vision_service)

        assert mock_processor_load.call_count == 0
        assert mock_model_load.call_count == 0


def test_vision_service_has_no_eager_class_level_model():
    # A class-level `model`/`processor` attribute evaluated at class-body
    # execution time is exactly the eager pattern being removed here.
    assert "model" not in vars(vision_service.VisionService)
    assert "processor" not in vars(vision_service.VisionService)


# ---------------------------------------------------------------------------
# Lazy load on first use, reused afterwards
# ---------------------------------------------------------------------------

def test_first_call_lazily_loads_model_and_processor():
    with patch.object(
        vision_service.BlipProcessor, "from_pretrained"
    ) as mock_processor_load, patch.object(
        vision_service.BlipForConditionalGeneration, "from_pretrained"
    ) as mock_model_load:

        mock_processor_load.side_effect = lambda *a, **k: MagicMock()
        mock_model_load.side_effect = lambda *a, **k: MagicMock()

        model, processor = (
            vision_service.VisionService._get_model_and_processor()
        )

        assert model is not None
        assert processor is not None
        assert mock_processor_load.call_count == 1
        assert mock_model_load.call_count == 1


def test_same_thread_reuses_its_own_instance():
    with patch.object(
        vision_service.BlipProcessor, "from_pretrained"
    ) as mock_processor_load, patch.object(
        vision_service.BlipForConditionalGeneration, "from_pretrained"
    ) as mock_model_load:

        mock_processor_load.side_effect = lambda *a, **k: MagicMock()
        mock_model_load.side_effect = lambda *a, **k: MagicMock()

        model_1, processor_1 = (
            vision_service.VisionService._get_model_and_processor()
        )
        model_2, processor_2 = (
            vision_service.VisionService._get_model_and_processor()
        )

        assert model_1 is model_2
        assert processor_1 is processor_2
        assert mock_model_load.call_count == 1
        assert mock_processor_load.call_count == 1


def test_different_threads_get_different_model_instances():
    with patch.object(
        vision_service.BlipProcessor, "from_pretrained"
    ) as mock_processor_load, patch.object(
        vision_service.BlipForConditionalGeneration, "from_pretrained"
    ) as mock_model_load:

        mock_processor_load.side_effect = lambda *a, **k: MagicMock()
        mock_model_load.side_effect = lambda *a, **k: MagicMock()

        seen: dict = {}

        def worker(name: str):
            seen[name] = (
                vision_service.VisionService._get_model_and_processor()
            )

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
        assert mock_model_load.call_count == len(threads)


# ---------------------------------------------------------------------------
# Behavior preservation: analyze_frame's public contract is unchanged
# ---------------------------------------------------------------------------

def test_analyze_frame_returns_same_shape_as_before(tmp_path):
    from PIL import Image

    image_path = tmp_path / "frame.jpg"
    Image.new("RGB", (4, 4)).save(image_path)

    with patch.object(
        vision_service.BlipProcessor, "from_pretrained"
    ) as mock_processor_load, patch.object(
        vision_service.BlipForConditionalGeneration, "from_pretrained"
    ) as mock_model_load:

        fake_processor = MagicMock()
        fake_processor.return_value = {"pixel_values": "fake_tensor"}
        fake_processor.decode.return_value = "a person playing a video game"

        fake_model = MagicMock()
        fake_model.generate.return_value = [[1, 2, 3]]

        mock_processor_load.return_value = fake_processor
        mock_model_load.return_value = fake_model

        result = vision_service.VisionService.analyze_frame(str(image_path))

        assert result == {
            "image": str(image_path),
            "description": "a person playing a video game",
        }
        fake_model.generate.assert_called_once()
        fake_processor.decode.assert_called_once_with(
            [1, 2, 3], skip_special_tokens=True
        )
