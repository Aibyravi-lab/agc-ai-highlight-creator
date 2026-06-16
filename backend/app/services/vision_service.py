from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image


class VisionService:

    # Load AI model once when service starts
    processor = BlipProcessor.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )

    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )


    @classmethod
    def analyze_frame(cls, image_path: str):

        image = Image.open(image_path).convert("RGB")

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