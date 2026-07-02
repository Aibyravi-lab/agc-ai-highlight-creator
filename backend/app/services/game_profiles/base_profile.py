from abc import ABC, abstractmethod


class BaseProfile(ABC):

    @property
    @abstractmethod
    def game_name(self) -> str: ...

    @property
    @abstractmethod
    def aliases(self) -> list[str]: ...

    @property
    @abstractmethod
    def clip_positive_prompts(self) -> dict[str, list[str]]: ...

    @property
    @abstractmethod
    def clip_negative_prompts(self) -> dict[str, list[str]]: ...

    @property
    @abstractmethod
    def priority_actions(self) -> list[str]: ...

    @property
    @abstractmethod
    def thumbnail_preferences(self) -> dict: ...

    @property
    @abstractmethod
    def metadata(self) -> dict: ...

    @property
    def scoring_weights(self) -> dict[str, float] | None:
        return None

    @property
    def category_weight_overrides(self) -> dict[str, float] | None:
        return None

    @property
    def ranking_bonus(self) -> dict[str, float]:
        return {}

    @property
    def max_highlights_per_category(self) -> int | None:
        return None

    def get_all_prompts(self) -> list[dict]:
        result = []
        for category, prompts in {
            **self.clip_positive_prompts,
            **self.clip_negative_prompts
        }.items():
            for prompt in prompts:
                result.append({"category": category, "prompt": prompt})
        return result

    def get_positive_categories(self) -> list[str]:
        return list(self.clip_positive_prompts.keys())

    def get_negative_categories(self) -> list[str]:
        return list(self.clip_negative_prompts.keys())


class DefaultProfile(BaseProfile):

    @property
    def game_name(self) -> str:
        return "Default"

    @property
    def aliases(self) -> list[str]:
        return []

    @property
    def clip_positive_prompts(self) -> dict[str, list[str]]:
        return {
            "combat": [
                "player fighting enemies",
                "combat encounter",
                "gunfire action",
                "battle sequence",
                "intense combat scene"
            ],
            "vehicle": [
                "vehicle driving action",
                "truck driving gameplay",
                "high speed vehicle movement",
                "racing gameplay",
                "car chase action"
            ],
            "action": [
                "intense gameplay moment",
                "fast paced game scene",
                "high action sequence",
                "exciting gameplay"
            ],
            "victory": [
                "victory screen",
                "mission completed",
                "achievement unlocked",
                "winner celebration"
            ],
            "danger": [
                "critical game situation",
                "boss battle",
                "player under attack",
                "survival moment"
            ]
        }

    @property
    def clip_negative_prompts(self) -> dict[str, list[str]]:
        return {
            "exploration": [
                "open world exploration",
                "player exploring environment",
                "traveling through game world",
                "adventure gameplay"
            ]
        }

    @property
    def priority_actions(self) -> list[str]:
        return ["combat", "danger", "victory"]

    @property
    def thumbnail_preferences(self) -> dict:
        return {"prefer_action": True}

    @property
    def metadata(self) -> dict:
        return {"version": "1.0"}
