"""VED-P1-018-B: defer the heavy ML package import chain out of app.main's
module-import path.

P1-018-B profiling (see docs) proved that importing app.main pulls in
torch, transformers, whisper and cv2 at module-import time -- before
FastAPI() is constructed or the socket is bound -- via
background_job_service -> pipeline_service -> clip_service/whisper_service,
and via the vision router -> vision_service, and via the scoring package's
motion/scene scorers -> vision_service/scene_service, and via
thumbnail_rank_service -> the thumbnail scorers. All three model classes
(BLIP, CLIP, Whisper) already lazy-load their *weights* on first use
(VED-P1-003, VED-P1-018-A); this is a separate, larger cost -- the PACKAGE
IMPORT itself (~7s locally, ~86% of total app.main import time) -- that
weight-laziness never touched.

This regression test must run in a fresh subprocess, not in-process. Many
other tests in this suite import clip_service/whisper_service/vision_service
directly (test_ai_inference_concurrency.py, test_vision_service_lazy_loading.py,
etc.), which permanently populates sys.modules with torch/transformers/
whisper/cv2 for the rest of that pytest process. An in-process check of
sys.modules after those tests have run would be trivially wrong regardless
of whether app.main itself imports them, so a clean interpreter is the only
reliable way to isolate app.main's own import graph.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent

HEAVY_MODULES = ("torch", "transformers", "whisper", "cv2")

_CHECK_SCRIPT = (
    "import sys\n"
    "import app.main\n"
    "heavy_loaded = [m for m in {modules!r} if m in sys.modules]\n"
    "if heavy_loaded:\n"
    "    print('HEAVY_MODULES_LOADED:' + ','.join(heavy_loaded))\n"
    "else:\n"
    "    print('OK')\n"
).format(modules=HEAVY_MODULES)


def _import_app_main_in_subprocess() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _CHECK_SCRIPT],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_importing_app_main_does_not_load_heavy_ml_packages():
    """Regression guard for VED-P1-018-B: app.main must be importable --
    i.e. Uvicorn must be able to construct/load the ASGI app and bind the
    socket -- without pulling torch/transformers/whisper/cv2 into memory.
    Those packages should only load once a pipeline job or a vision/scoring
    call site actually needs them.
    """
    result = _import_app_main_in_subprocess()

    assert result.returncode == 0, (
        "importing app.main failed in a clean subprocess:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )

    assert "OK" in result.stdout, (
        "app.main's import graph eagerly loaded one or more heavy ML "
        f"packages that must be deferred to first real use:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_first_real_pipeline_use_still_configures_torch_correctly():
    """VED-P1-018-B requirement: 'first real pipeline request must still
    work' / 'deterministic and production-safe'. Exercises the actual new
    code (PipelineService._ensure_torch_configured), not a mock of it --
    a real (unmocked) `import torch` + torch.set_num_threads() call, run
    against the real app.config.config.settings.MAX_CONCURRENT_JOBS value,
    proving the thread-count configuration that used to run unconditionally
    in app.main still runs correctly once deferred to first use.
    """
    import torch

    from app.config.config import settings
    from app.services.pipeline_service import PipelineService

    original_flag = PipelineService._torch_configured
    PipelineService._torch_configured = False

    try:
        PipelineService._ensure_torch_configured()

        assert PipelineService._torch_configured is True

        expected_threads = max(
            1,
            (os.cpu_count() or 4) // settings.MAX_CONCURRENT_JOBS
        )
        assert torch.get_num_threads() == expected_threads

        # Idempotent: a second call (e.g. a second concurrent pipeline
        # worker) must not raise and must remain configured.
        PipelineService._ensure_torch_configured()
        assert PipelineService._torch_configured is True

    finally:
        PipelineService._torch_configured = original_flag


@pytest.mark.parametrize(
    "module_path,attr_name",
    [
        ("app.services.pipeline_service", "ClipService"),
        ("app.services.pipeline_service", "WhisperService"),
    ],
)
def test_deferred_service_attrs_still_resolve_for_mocking(module_path, attr_name):
    """Existing tests patch these via string paths, e.g.
    patch("app.services.pipeline_service.ClipService.get_highlight_result").
    unittest.mock resolves that by getattr()-ing 'ClipService' off the
    pipeline_service module -- this must keep working even though the
    import is no longer eager, via pipeline_service.__getattr__.
    """
    import importlib

    module = importlib.import_module(module_path)
    resolved = getattr(module, attr_name)

    assert resolved.__name__ == attr_name
