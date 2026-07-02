"""Lightweight stage-timing instrumentation for PipelineService (AGC-036.1).

Investigation-only utility: records how long each pipeline stage takes so
bottlenecks can be identified. Does not alter pipeline behavior or outputs.
"""
import time
from types import TracebackType

from app.services.logger_service import LoggerService


class PipelineProfiler:

    # Internal stage key -> printed report label (order = printed order).
    STAGE_ORDER: list[str] = [
        "Frame Extraction",
        "CLIP Detection",
        "Motion Detection",
        "Scene Detection",
        "Audio Detection",
        "Highlight Scoring",
        "Diversity Filtering",
        "Clip Extraction",
        "Thumbnail Generation",
        "Reel Generation",
        "Vertical Reel Generation",
        "Whisper Audio Extraction",
        "Whisper Model Initialization",
        "Whisper Inference",
        "Whisper Post Processing",
        "Caption Rendering",
        "Caption Burn-in (FFmpeg)",
        "Caption Export",
        "Metadata Generation",
        "Result Export",
        "History Registration",
        "Project Registration",
    ]

    REPORT_LABELS: dict[str, str] = {
        "Frame Extraction": "Frame Extraction",
        "CLIP Detection": "CLIP Detection",
        "Motion Detection": "Motion Detection",
        "Scene Detection": "Scene Detection",
        "Audio Detection": "Audio Detection",
        "Highlight Scoring": "Highlight Scoring",
        "Diversity Filtering": "Diversity Filtering",
        "Clip Extraction": "Clip Extraction",
        "Thumbnail Generation": "Thumbnail Generation",
        "Reel Generation": "Reel Generation",
        "Vertical Reel Generation": "Vertical Reel",
        "Whisper Audio Extraction": "Whisper Audio Extraction",
        "Whisper Model Initialization": "Whisper Model Init",
        "Whisper Inference": "Whisper Inference",
        "Whisper Post Processing": "Whisper Post-Processing",
        "Caption Rendering": "Caption Rendering",
        "Caption Burn-in (FFmpeg)": "Caption Burn-in (FFmpeg)",
        "Caption Export": "Caption Export",
        "Metadata Generation": "Metadata",
        "Result Export": "Result Export",
        "History Registration": "History Registration",
        "Project Registration": "Project Registration",
    }

    LABEL_WIDTH = 26

    def __init__(self) -> None:
        self._durations: dict[str, float] = {
            stage: 0.0 for stage in self.STAGE_ORDER
        }
        self._job_start = time.perf_counter()

    def add(self, stage: str, duration_seconds: float) -> None:
        self._durations[stage] = (
            self._durations.get(stage, 0.0) + duration_seconds
        )

    def track(self, stage: str) -> "_StageTimer":
        return _StageTimer(self, stage)

    def build_report(self) -> str:
        total_seconds = time.perf_counter() - self._job_start

        lines = [
            "=========================================",
            "AGC Pipeline Performance Report",
            "=========================================",
            "",
        ]

        for stage in self.STAGE_ORDER:
            duration = self._durations.get(stage, 0.0)
            label = self.REPORT_LABELS[stage]
            lines.append(f"{label:<{self.LABEL_WIDTH}}: {duration:.2f} sec")

        lines.append("")
        lines.append("-----------------------------------------")
        lines.append(f"{'TOTAL':<{self.LABEL_WIDTH}}: {total_seconds:.2f} sec")
        lines.append("=========================================")

        return "\n".join(lines)

    def print_report(self) -> None:
        report = self.build_report()
        print(report)
        LoggerService.info(report)


class _StageTimer:
    """Context manager that adds its elapsed time to a PipelineProfiler stage."""

    def __init__(self, profiler: PipelineProfiler, stage: str) -> None:
        self._profiler = profiler
        self._stage = stage
        self._start = 0.0

    def __enter__(self) -> "_StageTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> bool:
        elapsed = time.perf_counter() - self._start
        self._profiler.add(self._stage, elapsed)
        return False
