import threading
import time
import whisper

from app.services.profiler_service import PipelineProfiler
from app.services.logger_service import LoggerService
from app.services.video_service import has_audio_stream


class WhisperService:

    # VED-P1-003: the model used to be a single process-wide singleton
    # guarded by a global lock, because concurrent background job threads
    # calling transcribe() on the same instance raced on its internal
    # decode buffers and crashed the process under concurrent load. That
    # lock fully serialized transcription across every concurrent job.
    # Each ThreadPoolExecutor worker thread now lazily loads and keeps its
    # own model instance, so there is no cross-thread mutable state left
    # to race on and no lock is needed.
    _thread_local = threading.local()

    @classmethod
    def get_model(cls):

        if not hasattr(cls._thread_local, "model"):

            print(
                "Loading Whisper model..."
            )

            cls._thread_local.model = whisper.load_model(
                "base"
            )

        return cls._thread_local.model

    @staticmethod
    def _neutral_transcription() -> dict:

        return {
            "text": "",
            "segments": [],
            "language": None
        }

    @classmethod
    def transcribe_video(
        cls,
        video_path: str,
        profiler: PipelineProfiler | None = None
    ):

        if not has_audio_stream(video_path):

            LoggerService.info(
                f"No audio stream found in {video_path} — "
                "skipping transcription"
            )

            return cls._neutral_transcription()

        if profiler is None:

            model = cls.get_model()
            result = model.transcribe(
                video_path
            )

            return result

        model_init_start = time.perf_counter()
        model = cls.get_model()
        profiler.add(
            "Whisper Model Initialization",
            time.perf_counter() - model_init_start
        )

        audio_extraction_start = time.perf_counter()
        audio = whisper.audio.load_audio(
            video_path
        )
        profiler.add(
            "Whisper Audio Extraction",
            time.perf_counter() - audio_extraction_start
        )

        inference_start = time.perf_counter()
        result = model.transcribe(
            audio
        )
        profiler.add(
            "Whisper Inference",
            time.perf_counter() - inference_start
        )

        return result
