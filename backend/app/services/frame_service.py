import subprocess
from app.services.job_storage_service import JobStorageService


class FrameService:

    @staticmethod
    def extract_frames(
        video_path: str,
        job_id: str | None = None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_folder = (
            JobStorageService.subfolder(
                resolved_job_id,
                "frames"
            )
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
            frame_data,

            "duration":
            len(frames)

        }