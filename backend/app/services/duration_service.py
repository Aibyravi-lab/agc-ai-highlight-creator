class DurationService:

    @staticmethod
    def get_duration(
        action: str
    ):

        action = action.lower()

        if (
            "shootout" in action
            or "gunfight" in action
            or "combat" in action
        ):
            return 8

        if (
            "chase" in action
            or "pursuit" in action
        ):
            return 8

        if (
            "stunt" in action
            or "jump" in action
        ):
            return 7

        if (
            "explosion" in action
        ):
            return 7

        if (
            "driving" in action
            or "racing" in action
        ):
            return 6

        if (
            "victory" in action
            or "completed" in action
            or "ending" in action
        ):
            return 4

        return 5