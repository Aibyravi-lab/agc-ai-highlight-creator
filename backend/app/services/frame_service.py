import subprocess
from pathlib import Path
from datetime import datetime


class FrameService:

    @staticmethod
    def extract_frames(video_path: str):

        video_name = Path(video_path).stem

        current_time = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        output_folder = (
            Path("storage")
            / "frames"
            / f"{video_name}_{current_time}"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        output_pattern = str(
            output_folder / "frame_%04d.jpg"
        )

        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            "fps=1",
            output_pattern
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(
                f"Frame extraction failed: "
                f"{result.stderr}"
            )

        frames = sorted(
            output_folder.glob("*.jpg")
        )

        frame_data = []

        for index, frame in enumerate(frames):

            frame_data.append({

                "frame_name":
                frame.name,

                "frame_path":
                str(frame),

                "timestamp_second":
                index

            })

        return {

            "total_frames":
            len(frames),

            "frame_location":
            str(output_folder),

            "frames":
            frame_data
        }