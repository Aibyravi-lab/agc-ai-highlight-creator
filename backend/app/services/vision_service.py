from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import cv2


class VisionService:

    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    @classmethod
    def analyze_frame(cls, image_path: str):

        image = Image.open(
            image_path
        ).convert("RGB")

        inputs = cls.processor(
            image,
            return_tensors="pt"
        )

        output = cls.model.generate(
            **inputs,
            max_new_tokens=30
        )

        caption = cls.processor.decode(
            output[0],
            skip_special_tokens=True
        )

        return {
            "image": image_path,
            "description": caption
        }

    @staticmethod
    def calculate_motion_score(
        previous_frame_path: str,
        current_frame_path: str
    ):

        previous_frame = cv2.imread(
            previous_frame_path
        )

        current_frame = cv2.imread(
            current_frame_path
        )

        if (
            previous_frame is None
            or current_frame is None
        ):
            return 0.0

        previous_gray = cv2.cvtColor(
            previous_frame,
            cv2.COLOR_BGR2GRAY
        )

        current_gray = cv2.cvtColor(
            current_frame,
            cv2.COLOR_BGR2GRAY
        )

        frame_diff = cv2.absdiff(
            previous_gray,
            current_gray
        )

        motion_score = (
            frame_diff.mean() / 255
        )

        return float(
            round(motion_score, 4)
        )

    @staticmethod
    def calculate_caption_score(
        caption: str
    ):

        caption = caption.lower()

        score = 0.0

        positive_keywords = [

            "car",
            "sports car",
            "driving",
            "road",
            "street",
            "race",
            "racing",
            "vehicle",

            "gun",
            "weapon",
            "shooting",

            "police",

            "explosion",
            "fire",

            "heist",
            "mission",
            "robbery",

            "chase",
            "action"
        ]

        negative_keywords = [

            "standing",
            "person standing",

            "garage",
            "parking",

            "empty",

            "wall",
            "building interior",

            "room"
        ]

        for keyword in positive_keywords:

            if keyword in caption:
                score += 0.10

        for keyword in negative_keywords:

            if keyword in caption:
                score -= 0.15

        score = max(
            0.0,
            min(score, 1.0)
        )

        return round(score, 4)