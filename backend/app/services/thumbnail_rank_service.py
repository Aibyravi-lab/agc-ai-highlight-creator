class ThumbnailRankService:

    @staticmethod
    def get_thumbnail_score(image_path: str) -> float:
        # VED-P1-018-B: deferred -- ThumbnailOrchestrator's scorers import
        # cv2 at module scope; importing it here keeps it out of
        # app.main's import path (see the P1-018-B profiling report).
        from app.services.thumbnail import ThumbnailOrchestrator

        return ThumbnailOrchestrator.score(image_path)
