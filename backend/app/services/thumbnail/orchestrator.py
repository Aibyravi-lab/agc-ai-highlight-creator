import cv2

from app.services.thumbnail.brightness_scorer import BrightnessScorer
from app.services.thumbnail.contrast_scorer import ContrastScorer
from app.services.thumbnail.sharpness_scorer import SharpnessScorer
from app.services.thumbnail.blur_scorer import BlurScorer
from app.services.thumbnail.composition_scorer import CompositionScorer

_WEIGHTS: dict[str, float] = {
    "brightness": 0.25,
    "contrast": 0.25,
    "sharpness": 0.30,
    "blur": 0.10,
    "composition": 0.10,
}


class ThumbnailOrchestrator:

    @staticmethod
    def score(image_path: str) -> float:
        image = cv2.imread(image_path)

        if image is None:
            return 0.5

        scores: dict[str, float] = {
            "brightness": BrightnessScorer.score(image),
            "contrast": ContrastScorer.score(image),
            "sharpness": SharpnessScorer.score(image),
            "blur": BlurScorer.score(image),
            "composition": CompositionScorer.score(image),
        }

        final_score = sum(
            scores[key] * _WEIGHTS[key]
            for key in _WEIGHTS
        )

        return round(min(final_score, 1.0), 4)
