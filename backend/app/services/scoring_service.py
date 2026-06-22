class ScoringService:

    CATEGORY_WEIGHTS = {

        "combat": 1.50,

        "danger": 1.40,

        "victory": 1.30,

        "vehicle": 1.10,

        "action": 1.10,

        "exploration": 0.80

    }

    @classmethod
    def apply_category_weight(
        cls,
        score: float,
        category: str
    ):

        multiplier = (
            cls.CATEGORY_WEIGHTS.get(
                category.lower(),
                1.0
            )
        )

        weighted_score = (
            score * multiplier
        )

        return round(
            min(weighted_score, 1.0),
            4
        )

    @classmethod
    def apply_action_weight(
        cls,
        score: float,
        action: str
    ):

        action_lower = action.lower()

        if (
            "combat" in action_lower
            or
            "gunfire" in action_lower
            or
            "battle" in action_lower
        ):

            return cls.apply_category_weight(
                score,
                "combat"
            )

        if (
            "boss" in action_lower
            or
            "critical" in action_lower
            or
            "survival" in action_lower
        ):

            return cls.apply_category_weight(
                score,
                "danger"
            )

        if (
            "victory" in action_lower
            or
            "completed" in action_lower
            or
            "achievement" in action_lower
        ):

            return cls.apply_category_weight(
                score,
                "victory"
            )

        if (
            "vehicle" in action_lower
            or
            "driving" in action_lower
            or
            "truck" in action_lower
            or
            "racing" in action_lower
            or
            "chase" in action_lower
        ):

            return cls.apply_category_weight(
                score,
                "vehicle"
            )

        if (
            "exploration" in action_lower
            or
            "adventure" in action_lower
        ):

            return cls.apply_category_weight(
                score,
                "exploration"
            )

        return cls.apply_category_weight(
            score,
            "action"
        )