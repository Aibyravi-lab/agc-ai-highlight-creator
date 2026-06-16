import subprocess
from pathlib import Path
from datetime import datetime


class FrameService:

    @staticmethod
    def extract_frames(video_path: str):

        # Get video filename
        video_name = Path(video_path).stem

        # Create unique folder using timestamp
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_folder = (
            Path("storage")
            / "frames"
            / f"{video_name}_{current_time}"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        # Frame naming pattern
        output_pattern = str(
            output_folder / "frame_%04d.jpg"
        )

        # FFmpeg command
        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-vf",
            "fps=1",
            output_pattern
        ]

        # Execute FFmpeg
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        # Error handling
        if result.returncode != 0:
            raise Exception(
                f"Frame extraction failed: {result.stderr}"
            )

        # Get all generated frames
        frames = sorted(
            output_folder.glob("*.jpg")
        )

        # Prepare API response
        frame_data = []

        for index, frame in enumerate(frames):
            frame_data.append({
                "frame_name": frame.name,
                "timestamp_second": index + 1
            })

        return {
            "total_frames": len(frames),
            "frame_location": str(output_folder),
            "frames": frame_data
        }