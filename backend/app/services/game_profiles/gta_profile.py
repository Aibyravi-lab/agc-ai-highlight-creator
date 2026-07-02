from app.services.game_profiles.base_profile import BaseProfile


class GTAProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Grand Theft Auto V"

    @property
    def aliases(self) -> list[str]:
        return ["gta v", "gta5", "gta 5", "gtav", "grand theft auto", "gta"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "combat": [
                "GTA V shootout with police",
                "player shooting enemies in GTA",
                "gang war gunfight",
                "sniper shot gameplay",
                "drive-by shooting action"
            ],
            "vehicle": [
                "police car chase in GTA",
                "high speed getaway car",
                "motorcycle stunt jump",
                "supercar racing gameplay",
                "car crash explosion"
            ],
            "action": [
                "GTA heist action sequence",
                "intense wanted level escape",
                "parachute jump from skyscraper",
                "jet fighter combat",
                "tank rampage gameplay"
            ],
            "victory": [
                "GTA mission complete screen",
                "heist payout celebration",
                "criminal rank up achievement",
                "GTA Online win screen"
            ],
            "danger": [
                "five star wanted level",
                "surrounded by police in GTA",
                "low health critical moment",
                "RPG explosion danger"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "walking around Los Santos",
                "driving slowly on highway",
                "GTA cutscene dialogue",
                "peaceful city street in GTA"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["vehicle", "combat", "danger", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_action": True,
            "prefer_explosion": True,
            "prefer_vehicle": True
        }

    @property
    def category_weight_overrides(self) -> dict[str, float] | None:
        return {
            "vehicle": 1.30,
            "combat": 1.40,
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "open-world action",
            "platform": "PC/Console",
            "version": "1.0"
        }
