import subprocess
import time
from pathlib import Path

from app.config.config import settings
from app.services.profiler_service import PipelineProfiler


class CaptionService:

    @staticmethod
    def add_captions(
        video_path: str,
        caption_text: str,
        profiler: PipelineProfiler | None = None
    ):

        rendering_start = time.perf_counter()

        output_folder = Path(
            settings.HIGHLIGHT_FOLDER
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
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

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
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