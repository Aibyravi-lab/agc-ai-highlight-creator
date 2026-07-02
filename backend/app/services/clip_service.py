from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

from app.services.game_profiles.base_profile import BaseProfile, DefaultProfile


class ClipService:

    model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    @classmethod
    def get_all_prompts(
        cls,
        profile: BaseProfile | None = None
    ) -> list[dict]:

        if profile is None:
            profile = DefaultProfile()

        return profile.get_all_prompts()

    @classmethod
    def analyze_frame(
        cls,
        image_path: str,
        profile: BaseProfile | None = None
    ):

        if profile is None:
            profile = DefaultProfile()

        image = Image.open(
            image_path
        ).convert(
            "RGB"
        )

        prompt_objects = cls.get_all_prompts(profile)

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
        image_path: str,
        profile: BaseProfile | None = None
    ):

        if profile is None:
            profile = DefaultProfile()

        results = cls.analyze_frame(
            image_path,
            profile
        )

        top_results = results[:3]

        best_result = top_results[0]

        positive_categories = (
            profile.get_positive_categories()
        )

        negative_categories = (
            profile.get_negative_categories()
        )

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
