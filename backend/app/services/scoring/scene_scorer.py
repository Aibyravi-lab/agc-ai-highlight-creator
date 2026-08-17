class SceneScorer:

    @staticmethod
    def score(
        current_frame_path: str,
        previous_frame_path: str
    ) -> float:
        # VED-P1-018-B: deferred -- SceneService imports cv2 at module
        # scope; importing it here only on first real use keeps it out of
        # app.main's import path (see the P1-018-B profiling report).
        from app.services.scene_service import SceneService

        result = SceneService().analyze_frame(
            current_frame_path=current_frame_path,
            previous_frame_path=previous_frame_path
        )
        return result["scene_score"]
