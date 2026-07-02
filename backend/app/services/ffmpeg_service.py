import shutil
import subprocess


class FFmpegService:

    @staticmethod
    def validate():

        ffmpeg_path = shutil.which(
            "ffmpeg"
        )

        ffprobe_path = shutil.which(
            "ffprobe"
        )

        if not ffmpeg_path:

            raise RuntimeError(
                "FFmpeg not installed or not available in PATH"
            )

        if not ffprobe_path:

            raise RuntimeError(
                "FFprobe not installed or not available in PATH"
            )

        try:

            subprocess.run(
                [
                    "ffmpeg",
                    "-version"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            subprocess.run(
                [
                    "ffprobe",
                    "-version"
                ],
                capture_output=True,
                text=True,
                check=True
            )

        except Exception as error:

            raise RuntimeError(
                f"FFmpeg validation failed: {error}"
            )

        print(
            "FFmpeg Validation Passed"
        )