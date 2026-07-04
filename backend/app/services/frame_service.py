import os
import subprocess
from app.config.config import settings
from app.services.job_storage_service import JobStorageService
from app.services.logger_service import LoggerService


class FrameService:

    @staticmethod
    def extract_frames(
        video_path: str,
        job_id: str | None = None
    ):

        video_exists = os.path.exists(video_path)

        LoggerService.info(
            f"[AGC-049 DEBUG] frame_service.extract_frames — "
            f"received video_path={video_path}, "
            f"exists={video_exists}, "
            f"cwd={os.getcwd()}, "
            f"abs_path={os.path.abspath(video_path)}",
            job_id=job_id
        )

        if not video_exists:

            upload_dir = settings.UPLOAD_FOLDER

            try:
                listing = os.listdir(upload_dir)
            except Exception as error:
                listing = f"<could not list {upload_dir}: {error}>"

            LoggerService.info(
                f"[AGC-049 DEBUG] frame_service.extract_frames — "
                f"video_path missing, directory listing of {upload_dir}: {listing}",
                job_id=job_id
            )

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