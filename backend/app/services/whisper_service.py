import threading
import time
import whisper

from app.services.profiler_service import PipelineProfiler


class WhisperService:

    _model = None

    # Guards both lazy model creation (the check-then-load below is not
    # atomic) and every call into the shared model afterwards: concurrent
    # background job threads calling transcribe() on the same instance
    # race on its internal decode buffers, which has crashed the process
    # under concurrent load in production.
    _lock = threading.Lock()

    @classmethod
    def get_model(cls):

        if cls._model is None:

            print(
                "Loading Whisper model..."
            )

            cls._model = whisper.load_model(
                "base"
            )

        return cls._model

    @classmethod
    def transcribe_video(
        cls,
        video_path: str,
        profiler: PipelineProfiler | None = None
    ):

        if profiler is None:

            with cls._lock:
                model = cls.get_model()
                result = model.transcribe(
                    video_path
                )

            return result

        with cls._lock:

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
