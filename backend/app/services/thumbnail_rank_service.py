from app.services.thumbnail import ThumbnailOrchestrator


class ThumbnailRankService:

    @staticmethod
    def get_thumbnail_score(image_path: str) -> float:
        return ThumbnailOrchestrator.score(image_path)
