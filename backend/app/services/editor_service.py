import subprocess
import time
from pathlib import Path

from app.config.config import settings
class EditorService:

    @staticmethod
    def create_thumbnail(
        video_path: str,
        timestamp: int
    ):

        thumbnail_folder = Path(
            settings.THUMBNAIL_FOLDER
        )

        thumbnail_folder.mkdir(
            parents=True,
            exist_ok=True
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
        duration: int
    ):

        output_folder = Path(
            settings.HIGHLIGHT_FOLDER
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
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
                timestamp=timestamp
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