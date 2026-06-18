import whisper


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
        video_path: str
    ):

        model = cls.get_model()

        result = model.transcribe(
            video_path
        )

        return result