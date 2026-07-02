from app.services.game_profiles.base_profile import BaseProfile


class SnowRunnerProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "SnowRunner"

    @property
    def aliases(self) -> list[str]:
        return ["snowrunner", "snow runner", "spintires"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "vehicle": [
                "truck stuck in deep mud SnowRunner",
                "heavy truck crossing river",
                "SnowRunner winch recovery operation",
                "off-road truck climbing steep hill",
                "cargo delivery truck SnowRunner"
            ],
            "action": [
                "SnowRunner truck tipping over",
                "dramatic truck recovery SnowRunner",
                "truck crossing flooded road",
                "extreme terrain challenge SnowRunner",
                "truck sliding on ice SnowRunner"
            ],
            "victory": [
                "SnowRunner mission objective complete",
                "cargo delivered successfully",
                "SnowRunner contract completion screen",
                "truck reaching destination SnowRunner"
            ],
            "danger": [
                "truck sinking in deep water",
                "SnowRunner vehicle rollover moment",
                "truck severely stuck in snow",
                "dangerous cliff edge driving"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "truck driving on empty highway",
                "SnowRunner map overview screen",
                "idle parked truck SnowRunner",
                "slow flat road driving SnowRunner"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["vehicle", "action", "danger", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_vehicle": True,
            "prefer_mud": True
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
            "exploration": 1.20,
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "off-road simulation",
            "platform": "PC/Console",
            "version": "1.0"
        }
