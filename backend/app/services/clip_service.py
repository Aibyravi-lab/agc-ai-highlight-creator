from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

from app.config.game_events import GAME_EVENTS


class ClipService:

    model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    @classmethod
    def get_all_prompts(cls):

        prompts = []

        for category, category_prompts in GAME_EVENTS.items():

            for prompt in category_prompts:

                prompts.append(
                    {
                        "category": category,
                        "prompt": prompt
                    }
                )

        return prompts

    @classmethod
    def analyze_frame(
        cls,
        image_path: str
    ):

        image = Image.open(
            image_path
        ).convert(
            "RGB"
        )

        prompt_objects = cls.get_all_prompts()

        prompt_texts = [

            item["prompt"]

            for item in prompt_objects

        ]

        inputs = cls.processor(
            text=prompt_texts,
            images=image,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():

            outputs = cls.model(
                **inputs
            )

        scores = (
            outputs.logits_per_image
            .softmax(dim=1)[0]
        )

        results = []

        for item, score in zip(
            prompt_objects,
            scores
        ):

            results.append(
                {
                    "category":
                    item["category"],

                    "prompt":
                    item["prompt"],

                    "score":
                    float(score)
                }
            )

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results

    @classmethod
    def get_highlight_result(
        cls,
        image_path: str
    ):

        results = cls.analyze_frame(
            image_path
        )

        top_results = results[:3]

        best_result = top_results[0]

        positive_categories = [

            "combat",
            "vehicle",
            "action",
            "victory",
            "danger"

        ]

        negative_categories = [

            "exploration"

        ]

        is_positive = (
            best_result["category"]
            in positive_categories
        )

        is_negative = (
            best_result["category"]
            in negative_categories
        )

        is_highlight = (

            is_positive
            and not is_negative

        )

        return {

            "category":
            best_result["category"],

            "best_match":
            best_result["prompt"],

            "score":
            best_result["score"],

            "is_highlight":
            is_highlight,

            "top_matches":
            top_results

        }