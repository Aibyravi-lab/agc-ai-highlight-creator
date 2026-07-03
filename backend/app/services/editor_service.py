import subprocess
import time

from app.services.job_storage_service import JobStorageService
class EditorService:

    @staticmethod
    def create_thumbnail(
        video_path: str,
        timestamp: int,
        job_id: str | None = None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        thumbnail_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "thumbnails"
            )
        )

        thumbnail_path = (
            thumbnail_folder /
            f"thumbnail_{timestamp}.jpg"
        )

        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            video_path,
            "-frames:v",
            "1",
            str(thumbnail_path)
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(
                    result.stderr
                )

        except subprocess.TimeoutExpired:

            raise Exception(
                "Thumbnail generation timeout"
            )

        return str(
            thumbnail_path
        )

    @staticmethod
    def create_clip(
        video_path: str,
        timestamp: int,
        duration: int,
        job_id: str | None = None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "clips"
            )
        )

        output_path = (
            output_folder /
            f"highlight_{timestamp}.mp4"
        )

        command = [
            "ffmpeg",
            "-y",

            "-ss",
            str(timestamp),

            "-i",
            video_path,

            "-t",
            str(duration),

            "-c:v",
            "libx264",

            "-c:a",
            "aac",

            "-preset",
            "fast",

            str(output_path)
        ]

        clip_start = time.perf_counter()

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                raise Exception(
                    f"Clip creation failed: "
                    f"{result.stderr}"
                )

        except subprocess.TimeoutExpired:

            raise Exception(
                f"FFmpeg timeout at "
                f"timestamp {timestamp}"
            )

        clip_creation_seconds = (
            time.perf_counter() - clip_start
        )

        thumbnail_start = time.perf_counter()

        thumbnail_path = (
            EditorService.create_thumbnail(
                video_path=video_path,
                timestamp=timestamp,
                job_id=resolved_job_id
            )
        )

        thumbnail_generation_seconds = (
            time.perf_counter() - thumbnail_start
        )

        return {

            "clip_path":
            str(output_path),

            "thumbnail_path":
            thumbnail_path,

            "timestamp":
            timestamp,

            "duration":
            duration,

            "clip_creation_seconds":
            clip_creation_seconds,

            "thumbnail_generation_seconds":
            thumbnail_generation_seconds

        }