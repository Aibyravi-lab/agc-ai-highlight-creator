import subprocess

from app.config.config import settings
from app.services.cleanup_service import CleanupService
from app.services.job_storage_service import JobStorageService
class VideoEditorService:


    @staticmethod
    def create_clip(
        video_path: str,
        timestamp: int,
        duration: int = 5,
        job_id: str | None = None
    ):

        # Create output folder
        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "clips"
            )
        )


        # Clip name
        output_file = (
            output_folder
            / f"highlight_{timestamp}.mp4"
        )


        # FFmpeg command
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            video_path,
            "-t",
            str(duration),
            "-c",
            "copy",
            str(output_file)
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
                str(output_file)
            )

            raise Exception(
                f"Clip creation timed out at timestamp {timestamp}"
            )


        if result.returncode != 0:
            raise Exception(
                f"Clip creation failed: {result.stderr}"
            )


        return {
            "clip_path": str(output_file),
            "timestamp": timestamp,
            "duration": duration
        }