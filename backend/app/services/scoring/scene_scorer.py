from app.services.scene_service import SceneService


class SceneScorer:

    @staticmethod
    def score(
        current_frame_path: str,
        previous_frame_path: str
    ) -> float:
        result = SceneService().analyze_frame(
            current_frame_path=current_frame_path,
            previous_frame_path=previous_frame_path
        )
        return result["scene_score"]
