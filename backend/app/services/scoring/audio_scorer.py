from app.services.audio_service import AudioService


class AudioScorer:

    @staticmethod
    def score(
        audio_map: dict,
        timestamp: int
    ) -> float:
        return AudioService.get_audio_score(
            audio_map=audio_map,
            timestamp=timestamp
        )
