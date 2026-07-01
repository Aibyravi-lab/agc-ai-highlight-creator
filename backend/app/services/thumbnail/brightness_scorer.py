import cv2
import numpy as np


class BrightnessScorer:

    @staticmethod
    def score(image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = gray.mean() / 255
        return float(brightness)
