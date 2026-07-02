from app.services.game_profiles.base_profile import BaseProfile


class MinecraftProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Minecraft"

    @property
    def aliases(self) -> list[str]:
        return ["minecraft", "mine craft"]

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "combat": [
                "Minecraft player fighting boss mob",
                "Minecraft sword combat PvP",
                "Ender Dragon battle Minecraft",
                "Minecraft Wither boss fight",
                "Minecraft PvP arena combat"
            ],
            "action": [
                "Minecraft TNT explosion chain",
                "Minecraft redstone contraption activation",
                "large build reveal Minecraft",
                "Minecraft speedrun action sequence",
                "Minecraft parkour jump sequence"
            ],
            "victory": [
                "Minecraft Ender Dragon defeated",
                "Minecraft achievement popup unlock",
                "Minecraft boss loot drop",
                "Minecraft credits roll victory"
            ],
            "danger": [
                "Minecraft creeper explosion surprise",
                "Minecraft falling into lava",
                "Minecraft health critical moment",
                "Minecraft hardcore death screen"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "Minecraft walking through forest",
                "Minecraft mining in cave slowly",
                "Minecraft inventory management screen",
                "Minecraft crafting table menu"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["combat", "action", "danger", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {
            "prefer_action": True,
            "prefer_bright": True
        }

    @property
    def metadata(self) -> dict:
        return {
            "genre": "sandbox survival",
            "platform": "PC/Console",
            "version": "1.0"
        }
