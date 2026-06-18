import cv2
import numpy as np


class ThumbnailRankService:

    @staticmethod
    def calculate_brightness(image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        brightness = (
            gray.mean() / 255
        )

        return float(brightness)

    @staticmethod
    def calculate_contrast(image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        contrast = (
            gray.std() / 128
        )

        return min(
            float(contrast),
            1.0
        )

    @staticmethod
    def calculate_sharpness(image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        sharpness = cv2.Laplacian(
            gray,
            cv2.CV_64F
        ).var()

        sharpness = (
            sharpness / 1000
        )

        return min(
            float(sharpness),
            1.0
        )

    @classmethod
    def get_thumbnail_score(
        cls,
        image_path: str
    ):

        image = cv2.imread(
            image_path
        )

        if image is None:
            return 0.5

        brightness = (
            cls.calculate_brightness(
                image
            )
        )

        contrast = (
            cls.calculate_contrast(
                image
            )
        )

        sharpness = (
            cls.calculate_sharpness(
                image
            )
        )

        final_score = (

            brightness * 0.30

            +

            contrast * 0.30

            +

            sharpness * 0.40

        )

        return round(
            min(final_score, 1.0),
            4
        )