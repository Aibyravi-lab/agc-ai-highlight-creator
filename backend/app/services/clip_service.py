from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch


class ClipService:

    # Load model once
    model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32"
    )


    @classmethod
    def analyze_frame(cls, image_path: str):

        image = Image.open(image_path)

        prompts = [

            # GTA driving
            "a high speed car chase",
            "a car drifting on a road",
            "a car crash accident",
            "a vehicle driving fast",
            "a car jump stunt",

            # GTA action
            "a person shooting a gun",
            "a police chase in a city",
            "an explosion in a game",
            "an action scene from GTA",

            # Neutral
            "a person walking",
            "a character standing",
            "a normal scene"
        ]

        inputs = cls.processor(
            text=prompts,
            images=image,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = cls.model(**inputs)

        scores = (
            outputs.logits_per_image
            .softmax(dim=1)[0]
        )

        results = []

        for prompt, score in zip(prompts, scores):
            results.append({
                "prompt": prompt,
                "score": float(score)
            })

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results


    @classmethod
    def get_highlight_result(cls, image_path: str):

        results = cls.analyze_frame(image_path)

        best_result = results[0]

        highlight_keywords = [
            "chase",
            "drifting",
            "crash",
            "fast",
            "jump",
            "shooting",
            "explosion",
            "action"
        ]

        is_highlight = any(
            word in best_result["prompt"]
            for word in highlight_keywords
        )

        return {
            "best_match": best_result["prompt"],
            "score": best_result["score"],
            "is_highlight": is_highlight
        }