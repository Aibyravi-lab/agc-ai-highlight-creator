from app.services.game_profiles.base_profile import BaseProfile


class ValorantProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Valorant"

    @property
    def aliases(self) -> list[str]:
        return ["valorant", "valo"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "combat": [
                "Valorant gunfight first person shooter",
                "player landing headshot in Valorant",
                "multiple kills in Valorant",
                "Valorant ace round",
                "clutch 1v5 moment in Valorant"
            ],
            "action": [
                "Valorant agent ability activation",
                "Valorant spike plant action",
                "Valorant spike defuse action",
                "fast paced Valorant round",
                "Valorant entry frag sequence"
            ],
            "victory": [
                "Valorant round win screen",
                "Valorant match victory celebration",
                "Valorant rank up animation",
                "ace display in Valorant"
            ],
            "danger": [
                "Valorant clutch low health situation",
                "last alive in Valorant round",
                "Valorant 1v3 clutch attempt",
                "Valorant eco round desperation"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "Valorant buy phase screen",
                "walking Valorant map slowly",
                "Valorant loading screen",
                "Valorant lobby menu"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["combat", "action", "danger", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_action": True,
            "prefer_kill_feed": True
        }

    @property
    def scoring_weights(self) -> dict[str, float] | None:
        return {
            "clip": 0.40,
            "motion": 0.20,
            "scene": 0.15,
            "audio": 0.25,
            "duration": 0.00,
        }

    @property
    def category_weight_overrides(self) -> dict[str, float] | None:
        return {
            "combat": 1.60,
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "tactical FPS",
            "platform": "PC",
            "version": "1.0"
        }
