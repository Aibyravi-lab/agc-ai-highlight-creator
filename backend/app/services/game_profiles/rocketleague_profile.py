from app.services.game_profiles.base_profile import BaseProfile


class RocketLeagueProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Rocket League"

    @property
    def aliases(self) -> list[str]:
        return ["rocket league", "rocketleague", "rl"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "action": [
                "Rocket League aerial goal scored",
                "Rocket League bicycle kick goal",
                "amazing save in Rocket League",
                "Rocket League ceiling shot goal",
                "freestyle air dribble Rocket League"
            ],
            "vehicle": [
                "Rocket League boost speed dash",
                "Rocket League car flip reset",
                "Rocket League dribble challenge",
                "Rocket League supersonic speed play",
                "Rocket League wall drive shot"
            ],
            "victory": [
                "Rocket League goal explosion celebration",
                "Rocket League match win screen",
                "overtime goal Rocket League",
                "Rocket League last second goal"
            ],
            "danger": [
                "Rocket League 0 second goal",
                "Rocket League clutch save goalkeeper",
                "Rocket League comeback moment",
                "Rocket League overtime pressure"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "Rocket League kickoff slow start",
                "Rocket League menu screen lobby",
                "Rocket League idle positioning play",
                "Rocket League scoreboard view"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["action", "vehicle", "victory", "danger"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_action": True,
            "prefer_goal": True
        }

    @property
    def scoring_weights(self) -> dict[str, float] | None:
        return {
            "clip": 0.40,
            "motion": 0.30,
            "scene": 0.15,
            "audio": 0.15,
            "duration": 0.00,
        }

    @property
    def category_weight_overrides(self) -> dict[str, float] | None:
        return {
            "vehicle": 1.40,
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "vehicular soccer",
            "platform": "PC/Console",
            "version": "1.0"
        }
