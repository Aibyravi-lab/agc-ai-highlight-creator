import cv2
import numpy as np


class ContrastScorer:

    @staticmethod
    def score(image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contrast = gray.std() / 128
        return min(float(contrast), 1.0)
