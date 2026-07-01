class HighlightRankingService:

    MIN_TIMESTAMP_GAP: int = 45
    MAX_HIGHLIGHTS: int = 10
    MAX_PER_ACTION: int = 1

    @classmethod
    def rank(
        cls,
        candidates: list[dict]
    ) -> list[dict]:
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x["weighted_score"],
            reverse=True
        )

        action_counter: dict[str, int] = {}
        selected: list[dict] = []

        for candidate in sorted_candidates:

            action = candidate["action"]

            if action not in action_counter:
                action_counter[action] = 0

            if action_counter[action] >= cls.MAX_PER_ACTION:
                continue

            too_close = any(
                abs(
                    candidate["timestamp"]
                    - s["timestamp"]
                ) < cls.MIN_TIMESTAMP_GAP
                for s in selected
            )

            if too_close:
                continue

            action_counter[action] += 1
            selected.append(candidate)

            if len(selected) >= cls.MAX_HIGHLIGHTS:
                break

        return selected
