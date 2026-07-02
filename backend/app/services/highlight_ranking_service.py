from __future__ import annotations
from app.services.game_profiles.base_profile import BaseProfile


class HighlightRankingService:

    MIN_TIMESTAMP_GAP: int = 45
    MAX_HIGHLIGHTS: int = 10
    MAX_PER_ACTION: int = 1
    DIVERSITY_BONUS: float = 0.05

    @classmethod
    def _compute_ranking_score(
        cls,
        candidate: dict,
        selected: list[dict],
        profile_ranking_bonus: dict[str, float]
    ) -> float:
        weighted_score: float = candidate["weighted_score"]
        category: str = candidate.get("category", "").lower()

        profile_bonus = profile_ranking_bonus.get(category, 0.0)

        diversity_bonus = 0.0
        if selected and selected[-1].get("category", "").lower() != category:
            diversity_bonus = cls.DIVERSITY_BONUS

        return (
            weighted_score
            + diversity_bonus
            + profile_bonus
        )

    @classmethod
    def rank(
        cls,
        candidates: list[dict],
        profile: BaseProfile | None = None
    ) -> list[dict]:
        profile_ranking_bonus: dict[str, float] = (
            {k.lower(): v for k, v in profile.ranking_bonus.items()}
            if profile is not None
            else {}
        )
        max_per_category: int | None = (
            profile.max_highlights_per_category
            if profile is not None
            else None
        )

        def static_score(c: dict) -> float:
            cat = c.get("category", "").lower()
            return c["weighted_score"] + profile_ranking_bonus.get(cat, 0.0)

        sorted_candidates = sorted(
            candidates,
            key=static_score,
            reverse=True
        )

        action_counter: dict[str, int] = {}
        category_counter: dict[str, int] = {}
        selected: list[dict] = []

        for candidate in sorted_candidates:
            action: str = candidate["action"]
            category: str = candidate.get("category", "")

            if max_per_category is not None:
                if category_counter.get(category, 0) >= max_per_category:
                    continue
            else:
                if action not in action_counter:
                    action_counter[action] = 0
                if action_counter[action] >= cls.MAX_PER_ACTION:
                    continue

            too_close = any(
                abs(candidate["timestamp"] - s["timestamp"]) < cls.MIN_TIMESTAMP_GAP
                for s in selected
            )
            if too_close:
                continue

            ranking_score = cls._compute_ranking_score(
                candidate=candidate,
                selected=selected,
                profile_ranking_bonus=profile_ranking_bonus
            )
            candidate["ranking_score"] = round(ranking_score, 4)

            if max_per_category is not None:
                category_counter[category] = category_counter.get(category, 0) + 1
            else:
                action_counter[action] += 1

            selected.append(candidate)

            if len(selected) >= cls.MAX_HIGHLIGHTS:
                break

        return selected
