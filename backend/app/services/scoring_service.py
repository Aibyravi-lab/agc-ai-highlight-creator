class ScoringService:

    ACTION_WEIGHTS = {

        "driving": 1.00,

        "race": 1.10,
        "racing": 1.10,

        "chase": 1.20,
        "pursuit": 1.20,

        "shootout": 1.20,
        "gunfight": 1.20,
        "combat": 1.20,

        "explosion": 1.25,

        "stunt": 1.30,
        "jump": 1.30,

        "crash": 1.15,
        "collision": 1.15,

        "mission completed": 0.70,
        "victory": 0.70,
        "ending": 0.70
    }

    @classmethod
    def apply_action_weight(
        cls,
        score: float,
        action: str
    ):

        action_lower = action.lower()

        multiplier = 1.0

        for keyword, weight in (
            cls.ACTION_WEIGHTS.items()
        ):

            if keyword in action_lower:

                multiplier = weight
                break

        weighted_score = (
            score * multiplier
        )

        return round(
            min(weighted_score, 1.0),
            4
        )