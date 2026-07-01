CATEGORY_WEIGHTS: dict[str, float] = {
    "combat": 1.50,
    "danger": 1.40,
    "victory": 1.30,
    "vehicle": 1.10,
    "action": 1.10,
    "exploration": 0.80,
}

_WEIGHTS_NORMAL: dict[str, float] = {
    "clip": 0.50,
    "motion": 0.20,
    "scene": 0.15,
    "audio": 0.15,
    "duration": 0.00,
}

_WEIGHTS_SILENT: dict[str, float] = {
    "clip": 0.65,
    "motion": 0.20,
    "scene": 0.15,
    "audio": 0.00,
    "duration": 0.00,
}


class ScoringOrchestrator:

    @staticmethod
    def compute_base_score(
        clip_score: float,
        motion_score: float,
        audio_score: float,
        scene_score: float,
        duration_score: float,
        is_silent: bool
    ) -> float:
        weights = _WEIGHTS_SILENT if is_silent else _WEIGHTS_NORMAL
        return (
            clip_score * weights["clip"]
            + motion_score * weights["motion"]
            + scene_score * weights["scene"]
            + audio_score * weights["audio"]
            + duration_score * weights["duration"]
        )

    @staticmethod
    def apply_category_weight(
        score: float,
        category: str
    ) -> float:
        multiplier = CATEGORY_WEIGHTS.get(
            category.lower(),
            1.0
        )
        return round(
            min(score * multiplier, 1.0),
            4
        )

    @classmethod
    def apply_action_weight(
        cls,
        score: float,
        action: str
    ) -> float:
        action_lower = action.lower()

        if (
            "combat" in action_lower
            or "gunfire" in action_lower
            or "battle" in action_lower
        ):
            return cls.apply_category_weight(score, "combat")

        if (
            "boss" in action_lower
            or "critical" in action_lower
            or "survival" in action_lower
        ):
            return cls.apply_category_weight(score, "danger")

        if (
            "victory" in action_lower
            or "completed" in action_lower
            or "achievement" in action_lower
        ):
            return cls.apply_category_weight(score, "victory")

        if (
            "vehicle" in action_lower
            or "driving" in action_lower
            or "truck" in action_lower
            or "racing" in action_lower
            or "chase" in action_lower
        ):
            return cls.apply_category_weight(score, "vehicle")

        if (
            "exploration" in action_lower
            or "adventure" in action_lower
        ):
            return cls.apply_category_weight(score, "exploration")

        return cls.apply_category_weight(score, "action")

    @classmethod
    def compute_weighted_score(
        cls,
        clip_score: float,
        motion_score: float,
        audio_score: float,
        scene_score: float,
        duration_score: float,
        action: str,
        is_silent: bool
    ) -> float:
        base_score = cls.compute_base_score(
            clip_score=clip_score,
            motion_score=motion_score,
            audio_score=audio_score,
            scene_score=scene_score,
            duration_score=duration_score,
            is_silent=is_silent
        )
        return cls.apply_action_weight(
            score=base_score,
            action=action
        )
