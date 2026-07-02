import time
import whisper

from app.services.profiler_service import PipelineProfiler


class WhisperService:

    _model = None

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