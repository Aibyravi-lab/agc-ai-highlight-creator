import threading

from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import cv2


class VisionService:

    # VED-P1-018-A: BLIP used to load eagerly as class attributes,
    # evaluated the instant this module was imported -- before FastAPI
    # was constructed or the socket was bound, adding a live Hugging Face
    # Hub round-trip to every backend restart. Lazily loading per thread,
    # mirroring the ClipService/WhisperService pattern (VED-P1-003), moves
    # that cost to the first real inference call instead of the import
    # path.
    _thread_local = threading.local()

    @classmethod
    def _get_model_and_processor(cls):

        if not hasattr(cls._thread_local, "model"):

            cls._thread_local.model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )

            cls._thread_local.processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )

        return (
            cls._thread_local.model,
            cls._thread_local.processor
        )

    @classmethod
    def analyze_frame(cls, image_path: str):

        image = Image.open(
            image_path
        ).convert("RGB")

        model, processor = cls._get_model_and_processor()

        inputs = processor(
            image,
            return_tensors="pt"
        )

        output = model.generate(
            **inputs,
            max_new_tokens=30
        )

        caption = processor.decode(
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

