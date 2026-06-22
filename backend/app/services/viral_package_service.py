class ViralPackageService:

    @staticmethod
    def generate_package(
        highlights: list
    ):

        actions = []

        for highlight in highlights:

            action = (
                highlight["action"]
                .replace("a ", "")
                .replace("an ", "")
                .replace("scene", "")
                .strip()
            )

            if action not in actions:
                actions.append(action)

        title = "Epic Gaming Highlights"

        if len(actions) > 0:

            title = (
                " + ".join(
                    action.title()
                    for action in actions[:3]
                )
            )

            title += " Highlights"

        description = (
            "Watch the best gaming moments including "
            +
            ", ".join(actions[:5])
            +
            ". Generated automatically by AGC."
        )

        hashtags = [

            "#gaming",
            "#shorts",
            "#reels",
            "#viral",
            "#highlights"

        ]

        for action in actions[:3]:

            tag = (
                "#"
                + action
                .lower()
                .replace(" ", "")
                .replace("-", "")
            )

            if tag not in hashtags:

                hashtags.append(tag)

        return {

            "title":
            title,

            "description":
            description,

            "hashtags":
            hashtags

        }