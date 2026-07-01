import cv2
import numpy as np


class CompositionScorer:
    """Scores subject separation: rewards frames where center brightness differs from outer thirds."""

    @staticmethod
    def score(image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        center = gray[h // 3:2 * h // 3, w // 3:2 * w // 3]
        outer = np.concatenate([
            gray[:h // 3].flatten(),
            gray[2 * h // 3:].flatten(),
            gray[h // 3:2 * h // 3, :w // 3].flatten(),
            gray[h // 3:2 * h // 3, 2 * w // 3:].flatten(),
        ])
        center_mean = float(center.mean())
        outer_mean = float(outer.mean())
        separation = abs(center_mean - outer_mean) / 128
        return min(float(separation), 1.0)
