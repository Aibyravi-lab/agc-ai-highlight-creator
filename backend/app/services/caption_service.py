import subprocess
from pathlib import Path


class CaptionService:

    @staticmethod
    def add_captions(
        video_path: str,
        caption_text: str
    ):

        output_folder = Path(
            "storage/highlights"
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

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            raise Exception(
                result.stderr
            )

        return str(output_video)