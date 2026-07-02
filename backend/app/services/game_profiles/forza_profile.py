from app.services.game_profiles.base_profile import BaseProfile


class ForzaProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Forza"

    @property
    def aliases(self) -> list[str]:
        return ["forza", "forza horizon", "forza motorsport"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "vehicle": [
                "Forza racing car high speed",
                "Forza Horizon drift action",
                "supercar racing on track Forza",
                "Forza car crash spectacular",
                "Forza overtake close race"
            ],
            "action": [
                "Forza Horizon stunt jump",
                "Forza near miss racing moment",
                "drift competition Forza Horizon",
                "Forza speed zone record run",
                "Forza danger sign jump"
            ],
            "victory": [
                "Forza race win podium finish",
                "Forza Horizon championship win",
                "first place racing Forza",
                "Forza skill score chain"
            ],
            "danger": [
                "Forza last second overtake",
                "Forza crash into barrier",
                "spinning out in Forza race",
                "Forza photo finish race"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "Forza cruising slowly on road",
                "Forza Horizon map screen",
                "Forza car garage selection",
                "Forza loading screen menu"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["vehicle", "action", "victory", "danger"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_vehicle": True,
            "prefer_speed": True
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "racing",
            "platform": "PC/Xbox",
            "version": "1.0"
        }
