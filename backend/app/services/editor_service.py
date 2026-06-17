import subprocess
from pathlib import Path


class EditorService:

    @staticmethod
    def create_clip(
        video_path: str,
        timestamp: int,
        duration: int
    ):

        output_folder = Path(
            "storage/highlights"
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
            "-i",
            video_path,
            "-ss",
            str(timestamp),
            "-t",
            str(duration),
            "-c",
            "copy",
            str(output_path)
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
                    f"Clip creation failed: "
                    f"{result.stderr}"
                )

        except subprocess.TimeoutExpired:

            raise Exception(
                f"FFmpeg timeout at "
                f"timestamp {timestamp}"
            )

        return {
            "clip_path": str(output_path),
            "timestamp": timestamp,
            "duration": duration
        }