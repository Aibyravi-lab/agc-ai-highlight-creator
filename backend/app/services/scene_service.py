import cv2
from pathlib import Path


class SceneService:
    """
    Detect scene changes between consecutive frames.

    Returns:
        float score between 0.0 and 1.0

    Higher score:
        Bigger visual scene transition

    Lower score:
        Similar frame
    """

    def __init__(self):
        pass

    def calculate_scene_score(
        self,
        current_frame_path: str,
        previous_frame_path: str
    ) -> float:
        """
        Compare two frames and return scene change score.

        Args:
            current_frame_path (str)
            previous_frame_path (str)

        Returns:
            float
        """

        try:
            current_frame = cv2.imread(current_frame_path)
            previous_frame = cv2.imread(previous_frame_path)

            if current_frame is None:
                return 0.0

            if previous_frame is None:
                return 0.0

            current_hist = self._generate_histogram(current_frame)
            previous_hist = self._generate_histogram(previous_frame)

            similarity = cv2.compareHist(
                current_hist,
                previous_hist,
                cv2.HISTCMP_CORREL
            )

            scene_score = 1.0 - similarity

            scene_score = max(0.0, min(scene_score, 1.0))

            return round(scene_score, 4)

        except Exception as ex:
            print(
                f"[SCENE ERROR] "
                f"{Path(current_frame_path).name} : {ex}"
            )
            return 0.0

    def _generate_histogram(self, image):
        """
        Create normalized color histogram.
        """

        histogram = cv2.calcHist(
            [image],
            [0, 1, 2],
            None,
            [8, 8, 8],
            [0, 256, 0, 256, 0, 256]
        )

        cv2.normalize(histogram, histogram)

        return histogram

    def analyze_frame(
        self,
        current_frame_path: str,
        previous_frame_path: str
    ) -> dict:
        """
        Full scene analysis response.

        Returns:
        {
            "scene_score": float
        }
        """

        scene_score = self.calculate_scene_score(
            current_frame_path=current_frame_path,
            previous_frame_path=previous_frame_path
        )

        return {
            "scene_score": scene_score
        }