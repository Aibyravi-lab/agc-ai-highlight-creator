from __future__ import annotations
from app.config.config import settings
from app.services.scoring.orchestrator import CATEGORY_WEIGHTS


class ExplainabilityService:

    @staticmethod
    def _derive_category(action: str) -> str:
        a = action.lower()
        if "combat" in a or "gunfire" in a or "battle" in a:
            return "combat"
        if "boss" in a or "critical" in a or "survival" in a:
            return "danger"
        if "victory" in a or "completed" in a or "achievement" in a:
            return "victory"
        if "vehicle" in a or "driving" in a or "truck" in a or "racing" in a or "chase" in a:
            return "vehicle"
        if "exploration" in a or "adventure" in a:
            return "exploration"
        return "action"

    @classmethod
    def _get_category_multiplier(
        cls,
        action: str,
        category_overrides: dict[str, float] | None = None,
    ) -> float:
        cat = cls._derive_category(action)
        effective = (
            {**CATEGORY_WEIGHTS, **category_overrides}
            if category_overrides
            else CATEGORY_WEIGHTS
        )
        return effective.get(cat, 1.0)

    @staticmethod
    def _get_synergy_multiplier(
        clip_score: float,
        motion_score: float,
        scene_score: float,
        audio_score: float,
    ) -> float:
        if not settings.SYNERGY_ENABLED:
            return 1.0
        threshold = settings.SYNERGY_SIGNAL_THRESHOLD
        strong_count = sum(
            1 for s in (clip_score, motion_score, scene_score, audio_score)
            if s >= threshold
        )
        bonus = max(0, strong_count - 1)
        return min(1.0 + bonus * settings.SYNERGY_INCREMENT, settings.MAX_SYNERGY_MULTIPLIER)

    @classmethod
    def build(
        cls,
        clip_score: float,
        motion_score: float,
        scene_score: float,
        audio_score: float,
        duration_score: float,
        weighted_score: float,
        ranking_score: float,
        adaptive_threshold: float,
        profile_name: str,
        action: str,
        category: str,
        category_overrides: dict[str, float] | None = None,
        profile_ranking_bonus: dict[str, float] | None = None,
    ) -> dict:
        cat_mult = cls._get_category_multiplier(action, category_overrides)
        syn_mult = cls._get_synergy_multiplier(clip_score, motion_score, scene_score, audio_score)
        bonus_map = {k.lower(): v for k, v in (profile_ranking_bonus or {}).items()}
        profile_bonus = bonus_map.get(category.lower(), 0.0)

        threshold = settings.SYNERGY_SIGNAL_THRESHOLD
        reasons: list[str] = []
        if clip_score >= threshold:
            reasons.append("High CLIP confidence")
        if motion_score >= threshold:
            reasons.append("High motion")
        if scene_score >= threshold:
            reasons.append("Scene change detected")
        if audio_score >= threshold:
            reasons.append("Audio spike")
        if cat_mult > 1.0:
            reasons.append("Category bonus applied")
        if profile_bonus > 0.0:
            reasons.append("Profile bonus applied")
        if syn_mult > 1.0:
            reasons.append("Synergy activated")

        return {
            "clip_score": round(clip_score, 4),
            "motion_score": round(motion_score, 4),
            "scene_score": round(scene_score, 4),
            "audio_score": round(audio_score, 4),
            "duration_score": round(duration_score, 4),
            "weighted_score": round(weighted_score, 4),
            "ranking_score": round(ranking_score, 4),
            "adaptive_threshold": round(adaptive_threshold, 4),
            "profile_name": profile_name,
            "category_multiplier": round(cat_mult, 4),
            "synergy_multiplier": round(syn_mult, 4),
            "reasons": reasons,
        }
