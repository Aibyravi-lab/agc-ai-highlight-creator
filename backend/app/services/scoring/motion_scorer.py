class MotionScorer:

    @staticmethod
    def score(
        previous_frame_path: str,
        current_frame_path: str
    ) -> float:
        # VED-P1-018-B: deferred -- VisionService imports transformers/cv2
        # at module scope (see the P1-018-B profiling report); importing it
        # here only on first real use keeps it out of app.main's import path.
        from app.services.vision_service import VisionService

        return VisionService.calculate_motion_score(
            previous_frame_path,
            current_frame_path
        )
