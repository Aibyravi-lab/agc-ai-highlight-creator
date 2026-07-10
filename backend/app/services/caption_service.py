import subprocess
import time

from app.config.config import settings
from app.services.cleanup_service import CleanupService
from app.services.profiler_service import PipelineProfiler
from app.services.job_storage_service import JobStorageService


class CaptionService:

    @staticmethod
    def add_captions(
        video_path: str,
        caption_text: str,
        profiler: PipelineProfiler | None = None,
        job_id: str | None = None
    ):

        rendering_start = time.perf_counter()

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "captions"
            )
        )

        output_video = (
            output_folder /
            "captioned_reel.mp4"
        )

        safe_text = (
            caption_text
            .replace(":", "")
            .replace("'", "")
            [:100]
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            (
                f"drawtext="
                f"text='{safe_text}':"
                f"fontcolor=white:"
                f"fontsize=32:"
                f"x=(w-text_w)/2:"
                f"y=h-100"
            ),
            str(output_video)
        ]

        if profiler is not None:
            profiler.add(
                "Caption Rendering",
                time.perf_counter() - rendering_start
            )

        burn_in_start = time.perf_counter()

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.FFMPEG_SHORT_TIMEOUT_SECONDS
            )

        except subprocess.TimeoutExpired:

            CleanupService.cleanup_temp_file(
                str(output_video)
            )

            raise Exception(
                "Caption burn-in timed out"
            )

        if profiler is not None:
            profiler.add(
                "Caption Burn-in (FFmpeg)",
                time.perf_counter() - burn_in_start
            )

        export_start = time.perf_counter()

        if result.returncode != 0:

            raise Exception(
                result.stderr
            )

        output_path = str(output_video)

        if profiler is not None:
            profiler.add(
                "Caption Export",
                time.perf_counter() - export_start
            )

        return output_path