from app.services.game_profiles.base_profile import BaseProfile


class PUBGProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "PUBG: Battlegrounds"

    @property
    def aliases(self) -> list[str]:
        return ["pubg", "battlegrounds", "playerunknown", "player unknown"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "combat": [
                "PUBG gunfight long range",
                "battlegrounds sniper kill",
                "PUBG squad wipe moment",
                "close range shotgun fight PUBG",
                "PUBG kill streak action"
            ],
            "vehicle": [
                "PUBG buggy vehicle chase",
                "motorcycle jump battlegrounds",
                "PUBG driving into the zone",
                "vehicle road kill in PUBG",
                "boat escape in battlegrounds"
            ],
            "action": [
                "PUBG parachute landing drop",
                "final circle zone survival",
                "PUBG grenade throw action",
                "battlegrounds airdrop pickup",
                "PUBG prone crawl sprint"
            ],
            "victory": [
                "PUBG chicken dinner winner screen",
                "PUBG winner winner chicken dinner",
                "last player standing PUBG",
                "battlegrounds final kill victory"
            ],
            "danger": [
                "PUBG final zone circle shrink",
                "PUBG knocked out revive moment",
                "blue zone damage escape",
                "PUBG ambush caught in the open"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "PUBG looting house inventory",
                "crawling through grass slowly",
                "PUBG map view screen",
                "waiting in building PUBG"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["combat", "vehicle", "danger", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_action": True,
            "prefer_outdoor": True
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "battle royale",
            "platform": "PC/Console",
            "version": "1.0"
        }
