from app.services.duration_service import DurationService

_MAX_DURATION_SECONDS: float = 8.0


class DurationScorer:

    @staticmethod
    def score(action: str) -> float:
        duration = DurationService.get_duration(action)
        return round(
            min(float(duration) / _MAX_DURATION_SECONDS, 1.0),
            4
        )
