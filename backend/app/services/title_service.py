class TitleService:

    CATEGORY_TITLES = {

        "combat": [
            "Insane Combat Highlights",
            "Crazy Battle Moments",
            "Epic Combat Compilation"
        ],

        "danger": [
            "Dangerous Survival Moments",
            "Insane Near Misses",
            "Extreme Gaming Moments"
        ],

        "victory": [
            "Legendary Winning Moments",
            "Epic Victory Highlights",
            "Clutch Gaming Plays"
        ],

        "vehicle": [
            "Epic Driving Highlights",
            "High Speed Action Moments",
            "Ultimate Vehicle Gameplay"
        ],

        "action": [
            "Epic Action Highlights",
            "Insane Gameplay Moments",
            "Best Gaming Action"
        ],

        "exploration": [
            "Amazing Open World Adventure",
            "Epic Exploration Journey",
            "Beautiful Gaming Moments"
        ]

    }

    @classmethod
    def generate_title(
        cls,
        highlights: list
    ):

        if not highlights:

            return (
                "AI Gaming Highlights"
            )

        category_count = {}

        for highlight in highlights:

            category = (
                highlight.get(
                    "category",
                    "action"
                )
            )

            category_count[
                category
            ] = (

                category_count.get(
                    category,
                    0
                ) + 1

            )

        dominant_category = max(

            category_count,

            key=category_count.get

        )

        category_titles = (

            cls.CATEGORY_TITLES.get(
                dominant_category,
                cls.CATEGORY_TITLES[
                    "action"
                ]
            )

        )

        return category_titles[0]