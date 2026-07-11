import subprocess
import wave
import numpy as np
from app.config.config import settings
from app.services.cleanup_service import CleanupService
from app.services.job_storage_service import JobStorageService
from app.services.logger_service import LoggerService
from app.services.video_service import has_audio_stream


class NoAudioStreamError(Exception):
    """Raised when the input video has no audio stream to extract."""


class AudioService:

    @staticmethod
    def extract_audio(
        video_path: str,
        output_wav: str
    ):

        command = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            output_wav
        ]

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.FFMPEG_LONG_TIMEOUT_SECONDS
            )

        except subprocess.TimeoutExpired:

            CleanupService.cleanup_temp_file(
                output_wav
            )

            raise Exception(
                "Audio extraction timed out"
            )

        if result.returncode != 0:
            raise Exception(
                f"Audio extraction failed: "
                f"{result.stderr}"
            )

        return output_wav

    @classmethod
    def build_audio_map(
        cls,
        video_path: str,
        job_id: str | None = None
    ):

        try:

            resolved_job_id = (
                JobStorageService.resolve_job_id(job_id)
            )

            temp_folder = (
                JobStorageService.subfolder(
                    resolved_job_id,
                    "audio"
                )
            )

            wav_file = (
                temp_folder
                / "temp_audio.wav"
            )

            if not has_audio_stream(video_path):
                raise NoAudioStreamError(
                    f"No audio stream found in {video_path}"
                )

            cls.extract_audio(
                video_path=video_path,
                output_wav=str(wav_file)
            )

            with wave.open(
                str(wav_file),
                "rb"
            ) as audio:

                frame_rate = (
                    audio.getframerate()
                )

                total_frames = (
                    audio.getnframes()
                )

                raw_audio = (
                    audio.readframes(
                        total_frames
                    )
                )

            audio_data = np.frombuffer(
                raw_audio,
                dtype=np.int16
            )

            if len(audio_data) == 0:

                return {
                    "audio_map": {},
                    "is_silent": True
                }

            max_amplitude = np.max(
                np.abs(audio_data)
            )

            if max_amplitude == 0:

                return {
                    "audio_map": {},
                    "is_silent": True
                }

            audio_map = {}

            total_seconds = int(
                len(audio_data)
                / frame_rate
            )

            for second in range(
                total_seconds
            ):

                start_index = (
                    second
                    * frame_rate
                )

                end_index = (
                    start_index
                    + frame_rate
                )

                second_data = (
                    audio_data[
                        start_index:end_index
                    ]
                )

                if len(second_data) == 0:

                    audio_map[
                        second
                    ] = 0.0

                    continue

                peak = np.max(
                    np.abs(
                        second_data
                    )
                )

                score = (
                    peak
                    / max_amplitude
                )

                audio_map[
                    second
                ] = round(
                    float(score),
                    4
                )

            return {

                "audio_map":
                audio_map,

                "is_silent":
                False

            }

        except NoAudioStreamError:

            LoggerService.info(
                "No audio stream found in video — "
                "using neutral/silent audio score",
                job_id=job_id
            )

            return {

                "audio_map": {},

                "is_silent": True

            }

        except Exception as ex:

            print(
                f"[AUDIO ERROR] {ex}"
            )

            return {

                "audio_map": {},

                "is_silent": True

            }

    @classmethod
    def get_windowed_audio_score(
        cls,
        audio_map: dict,
        timestamp: int,
        window: int = 2
    ) -> float:

        if not audio_map:
            return 0.0

        scores = [
            audio_map[t]
            for t in range(
                timestamp - window,
                timestamp + window + 1
            )
            if t in audio_map
        ]

        if not scores:
            return 0.0

        return max(scores)