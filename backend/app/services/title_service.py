class TitleService:

    @staticmethod
    def generate_title(
        highlights: list
    ):

        if not highlights:

            return (
                "AI Gaming Highlights"
            )

        actions = []

        for highlight in highlights:

            action = (
                highlight["action"]
                .replace("a ", "")
                .replace("an ", "")
                .replace("scene", "")
                .strip()
            )

            actions.append(
                action.title()
            )

        unique_actions = []

        for action in actions:

            if action not in unique_actions:

                unique_actions.append(
                    action
                )

        top_actions = (
            unique_actions[:3]
        )

        title = (
            " + ".join(top_actions)
        )

        return (
            f"{title} Highlights"
        )