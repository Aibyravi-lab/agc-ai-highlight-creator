import subprocess
import time
from pathlib import Path

from app.config.config import settings
from app.services.cleanup_service import CleanupService
from app.services.job_storage_service import JobStorageService
class ReelService:

    @staticmethod
    def create_vertical_reel(
        input_video: str,
        job_id: str | None = None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "reels"
            )
        )

        vertical_video = (
            output_folder /
            "final_highlight_reel_vertical.mp4"
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            input_video,

            "-vf",
            (
                "crop="
                "ih*9/16:ih,"
                "scale=1080:1920"
            ),

            "-c:a",
            "copy",

            str(vertical_video)
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.FFMPEG_SHORT_TIMEOUT_SECONDS
            )

        except subprocess.TimeoutExpired:

            CleanupService.cleanup_temp_file(
                str(vertical_video)
            )

            raise Exception(
                "Vertical reel generation timed out"
            )

        if result.returncode != 0:

            print(result.stderr)

            raise Exception(
                f"Vertical reel failed: "
                f"{result.stderr}"
            )

        return str(
            vertical_video
        )

    @staticmethod
    def merge_clips(
        clip_paths: list,
        job_id: str | None = None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "reels"
            )
        )

        list_file = (
            output_folder /
            "clips.txt"
        )

        with open(
            list_file,
            "w",
            encoding="utf-8"
        ) as file:

            print("\nMerging clips:")

            for clip in clip_paths:

                absolute_path = (
                    Path(clip)
                    .resolve()
                    .as_posix()
                )

                print(
                    absolute_path
                )

                file.write(
                    f"file '{absolute_path}'\n"
                )

        final_video = (
            output_folder /
            "final_highlight_reel.mp4"
        )

        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(final_video)
        ]

        merge_start = time.perf_counter()

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.FFMPEG_SHORT_TIMEOUT_SECONDS
            )

        except subprocess.TimeoutExpired:

            CleanupService.cleanup_temp_file(
                str(final_video)
            )

            raise Exception(
                "Clip merge timed out"
            )

        if result.returncode != 0:

            print(
                result.stderr
            )

            raise Exception(
                f"Merge failed: "
                f"{result.stderr}"
            )

        reel_generation_seconds = (
            time.perf_counter() - merge_start
        )

        vertical_start = time.perf_counter()

        vertical_video = (
            ReelService.create_vertical_reel(
                str(final_video),
                job_id=resolved_job_id
            )
        )

        vertical_reel_seconds = (
            time.perf_counter() - vertical_start
        )

        return {

            "final_video":
            str(final_video),

            "vertical_video":
            str(vertical_video),

            "reel_generation_seconds":
            reel_generation_seconds,

            "vertical_reel_seconds":
            vertical_reel_seconds

        }