from app.services.vision_service import VisionService


class MotionScorer:

    @staticmethod
    def score(
        previous_frame_path: str,
        current_frame_path: str
    ) -> float:
        return VisionService.calculate_motion_score(
            previous_frame_path,
            current_frame_path
        )
