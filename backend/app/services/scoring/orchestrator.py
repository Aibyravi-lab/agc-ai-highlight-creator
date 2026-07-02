from app.config.config import settings

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
    def _validate_weights(weights: dict[str, float]) -> bool:
        if set(weights.keys()) != set(_WEIGHTS_NORMAL.keys()):
            return False
        return abs(sum(weights.values()) - 1.0) < 0.01

    @staticmethod
    def compute_base_score(
        clip_score: float,
        motion_score: float,
        audio_score: float,
        scene_score: float,
        duration_score: float,
        is_silent: bool,
        weights: dict[str, float] | None = None
    ) -> float:
        if is_silent:
            w = _WEIGHTS_SILENT
        elif weights is not None:
            w = weights
        else:
            w = _WEIGHTS_NORMAL
        return (
            clip_score * w["clip"]
            + motion_score * w["motion"]
            + scene_score * w["scene"]
            + audio_score * w["audio"]
            + duration_score * w["duration"]
        )

    @staticmethod
    def apply_category_weight(
        score: float,
        category: str,
        category_overrides: dict[str, float] | None = None
    ) -> float:
        effective = (
            {**CATEGORY_WEIGHTS, **category_overrides}
            if category_overrides
            else CATEGORY_WEIGHTS
        )
        multiplier = effective.get(category.lower(), 1.0)
        return round(min(score * multiplier, 1.0), 4)

    @classmethod
    def apply_action_weight(
        cls,
        score: float,
        action: str,
        category_overrides: dict[str, float] | None = None
    ) -> float:
        action_lower = action.lower()

        if (
            "combat" in action_lower
            or "gunfire" in action_lower
            or "battle" in action_lower
        ):
            return cls.apply_category_weight(score, "combat", category_overrides)

        if (
            "boss" in action_lower
            or "critical" in action_lower
            or "survival" in action_lower
        ):
            return cls.apply_category_weight(score, "danger", category_overrides)

        if (
            "victory" in action_lower
            or "completed" in action_lower
            or "achievement" in action_lower
        ):
            return cls.apply_category_weight(score, "victory", category_overrides)

        if (
            "vehicle" in action_lower
            or "driving" in action_lower
            or "truck" in action_lower
            or "racing" in action_lower
            or "chase" in action_lower
        ):
            return cls.apply_category_weight(score, "vehicle", category_overrides)

        if (
            "exploration" in action_lower
            or "adventure" in action_lower
        ):
            return cls.apply_category_weight(score, "exploration", category_overrides)

        return cls.apply_category_weight(score, "action", category_overrides)

    @staticmethod
    def compute_synergy_multiplier(
        clip_score: float,
        motion_score: float,
        scene_score: float,
        audio_score: float
    ) -> float:
        threshold = settings.SYNERGY_SIGNAL_THRESHOLD
        strong_count = sum(
            1 for s in (clip_score, motion_score, scene_score, audio_score)
            if s >= threshold
        )
        # Synergy bonus starts on the second agreeing signal
        bonus_signals = max(0, strong_count - 1)
        multiplier = 1.0 + bonus_signals * settings.SYNERGY_INCREMENT
        return min(multiplier, settings.MAX_SYNERGY_MULTIPLIER)

    @classmethod
    def compute_weighted_score(
        cls,
        clip_score: float,
        motion_score: float,
        audio_score: float,
        scene_score: float,
        duration_score: float,
        action: str,
        is_silent: bool,
        weights: dict[str, float] | None = None,
        category_overrides: dict[str, float] | None = None
    ) -> float:
        validated_weights: dict[str, float] | None = None
        if weights is not None:
            if cls._validate_weights(weights):
                validated_weights = weights
            else:
                print(
                    f"[SCORING] Invalid profile weights — "
                    f"sum={sum(weights.values()):.4f}, keys={set(weights.keys())} — "
                    f"falling back to global defaults"
                )
        base_score = cls.compute_base_score(
            clip_score=clip_score,
            motion_score=motion_score,
            audio_score=audio_score,
            scene_score=scene_score,
            duration_score=duration_score,
            is_silent=is_silent,
            weights=validated_weights
        )
        if settings.SYNERGY_ENABLED:
            synergy_multiplier = cls.compute_synergy_multiplier(
                clip_score=clip_score,
                motion_score=motion_score,
                scene_score=scene_score,
                audio_score=audio_score
            )
            base_score = base_score * synergy_multiplier
        return cls.apply_action_weight(
            score=base_score,
            action=action,
            category_overrides=category_overrides
        )
