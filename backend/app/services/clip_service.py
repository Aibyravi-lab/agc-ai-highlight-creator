from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch


class ClipService:

    model = CLIPModel.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    processor = CLIPProcessor.from_pretrained(
        "openai/clip-vit-base-patch32"
    )

    @classmethod
    def analyze_frame(cls, image_path: str):

        image = Image.open(
            image_path
        ).convert("RGB")

        prompts = [

            # Driving
            "a GTA car driving on a city road",
            "a sports car driving fast",
            "a vehicle speeding through traffic",
            "a car driving in a city",

            # Racing
            "a street racing scene",
            "a racing car competition",
            "a high speed race",

            # Drifting
            "a car drifting around a corner",
            "a vehicle performing a drift",

            # Police Chase
            "a police chase in a city",
            "a wanted level pursuit",
            "a police vehicle chasing a suspect",

            # Shootout
            "a GTA shootout scene",
            "a player firing a weapon",
            "a gunfight in a city",
            "a combat firefight",

            # Explosions
            "a massive explosion",
            "a vehicle explosion",
            "a building explosion",

            # Crashes
            "a vehicle crash",
            "a car collision",
            "a damaged vehicle accident",

            # Stunts
            "a vehicle stunt jump",
            "a car jumping through the air",
            "a dangerous stunt scene",

            # Missions
            "a GTA mission scene",
            "a mission objective",
            "a heist mission",
            "a robbery mission",

            # Victory
            "a mission completed screen",
            "a successful mission ending",
            "a victory scene",

            # Negative
            "a parked vehicle",
            "a character standing still",
            "an empty street",
            "a garage interior",
            "a loading screen",
            "a normal scene"
        ]

        inputs = cls.processor(
            text=prompts,
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

        for prompt, score in zip(
            prompts,
            scores
        ):

            results.append({

                "prompt":
                prompt,

                "score":
                float(score)

            })

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

        positive_keywords = [

            "driving",
            "race",
            "racing",
            "drift",
            "chase",
            "pursuit",

            "shootout",
            "gunfight",
            "combat",
            "weapon",

            "explosion",

            "crash",
            "collision",

            "stunt",
            "jump",

            "mission",
            "heist",
            "robbery",

            "victory",
            "completed",
            "ending"
        ]

        negative_keywords = [

            "parked",
            "standing",
            "empty",
            "garage",
            "loading",
            "normal"
        ]

        is_positive = any(

            keyword in best_result["prompt"]

            for keyword in positive_keywords

        )

        is_negative = any(

            keyword in best_result["prompt"]

            for keyword in negative_keywords

        )

        is_highlight = (

            is_positive
            and not is_negative

        )

        return {

            "best_match":
            best_result["prompt"],

            "score":
            best_result["score"],

            "is_highlight":
            is_highlight,

            "top_matches":
            top_results

        }