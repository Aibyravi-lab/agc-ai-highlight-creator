import cv2
import numpy as np


class SharpnessScorer:

    @staticmethod
    def score(image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var() / 1000
        return min(float(sharpness), 1.0)
