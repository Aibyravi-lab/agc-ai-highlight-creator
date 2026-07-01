import cv2
import numpy as np


class BlurScorer:
    """Scores edge strength via Sobel gradients — distinct from Laplacian-based sharpness."""

    @staticmethod
    def score(image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        blur_score = magnitude.mean() / 50
        return min(float(blur_score), 1.0)
