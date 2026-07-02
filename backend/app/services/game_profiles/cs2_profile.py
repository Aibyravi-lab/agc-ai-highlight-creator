from app.services.game_profiles.base_profile import BaseProfile


class CS2Profile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Counter-Strike 2"

    @property
    def aliases(self) -> list[str]:
        return ["cs2", "counter strike", "counter-strike", "csgo", "cs go", "cs:go"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "combat": [
                "Counter-Strike headshot kill",
                "CS2 gunfight multiple kills",
                "AWP sniper shot gameplay",
                "deagle one tap headshot",
                "CS2 spray down enemies"
            ],
            "action": [
                "CS2 bomb plant on site",
                "CS2 bomb defuse clutch",
                "smoke grenade play CS2",
                "flashbang blind kills",
                "CS2 molotov fire action"
            ],
            "victory": [
                "CS2 round win bomb explosion",
                "Counter-Strike match win screen",
                "CS2 MVP star highlight",
                "ace round celebration CS2"
            ],
            "danger": [
                "CS2 clutch 1v4 situation",
                "last player alive counter strike",
                "CS2 low health clutch round",
                "anti-eco round pressure"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "CS2 buy phase weapon purchase",
                "walking slowly through CS2 map",
                "CS2 match scoreboard screen",
                "Counter-Strike loading screen"
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
