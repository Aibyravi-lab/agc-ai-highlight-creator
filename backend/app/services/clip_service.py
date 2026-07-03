import threading

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

    # The model/processor above are shared singletons used by every
    # background job worker thread. Concurrent forward passes on the
    # same instance race on internal buffers (observed in production
    # as a bare Linear-layer repr surfacing as the job error), so all
    # inference through them is serialized here.
    _inference_lock = threading.Lock()

    @classmethod
    def get_all_prompts(
        cls,
        profile: BaseProfile | None = None
    ) -> list[dict]:

        if profile is None:
            profile = DefaultProfile()

        return profile.get_all_prompts()

    @staticmethod
    def _l2_normalize(embeds: torch.Tensor) -> torch.Tensor:
        # Mirrors CLIPModel.forward's internal normalization
        # (transformers' _get_vector_norm) exactly, op-for-op,
        # so cached text embeddings stay bit-identical to the
        # values a combined model(**inputs) call would produce.
        squared = torch.pow(embeds, 2)
        summed = torch.sum(squared, dim=-1, keepdim=True)
        norm = torch.pow(summed, 0.5)
        return embeds / norm

    @classmethod
    def _get_text_embeddings(
        cls,
        prompt_texts: list[str],
        text_embedding_cache: dict | None
    ) -> torch.Tensor:
        cache_key = tuple(prompt_texts)

        if (
            text_embedding_cache is not None
            and cache_key in text_embedding_cache
        ):
            return text_embedding_cache[cache_key]

        text_inputs = cls.processor(
            text=prompt_texts,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            text_outputs = cls.model.get_text_features(
                **text_inputs
            )

        text_embeds = cls._l2_normalize(
            text_outputs.pooler_output
        )

        if text_embedding_cache is not None:
            text_embedding_cache[cache_key] = text_embeds

        return text_embeds

    @classmethod
    def analyze_frame(
        cls,
        image_path: str,
        profile: BaseProfile | None = None,
        text_embedding_cache: dict | None = None
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

        with cls._inference_lock:

            text_embeds = cls._get_text_embeddings(
                prompt_texts,
                text_embedding_cache
            )

            image_inputs = cls.processor(
                images=image,
                return_tensors="pt"
            )

            with torch.no_grad():
                image_outputs = cls.model.get_image_features(
                    **image_inputs
                )

            image_embeds = cls._l2_normalize(
                image_outputs.pooler_output
            )

            with torch.no_grad():
                logits_per_text = (
                    torch.matmul(
                        text_embeds,
                        image_embeds.t()
                    )
                    * cls.model.logit_scale.exp()
                )

                logits_per_image = logits_per_text.t()

        scores = (
            logits_per_image
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
        profile: BaseProfile | None = None,
        text_embedding_cache: dict | None = None
    ):

        if profile is None:
            profile = DefaultProfile()

        results = cls.analyze_frame(
            image_path,
            profile,
            text_embedding_cache
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
