from pathlib import Path

from app.services.game_profiles.base_profile import BaseProfile, DefaultProfile
from app.services.game_profiles.gta_profile import GTAProfile
from app.services.game_profiles.valorant_profile import ValorantProfile
from app.services.game_profiles.cs2_profile import CS2Profile
from app.services.game_profiles.pubg_profile import PUBGProfile
from app.services.game_profiles.snowrunner_profile import SnowRunnerProfile
from app.services.game_profiles.forza_profile import ForzaProfile
from app.services.game_profiles.minecraft_profile import MinecraftProfile
from app.services.game_profiles.rocketleague_profile import RocketLeagueProfile


_PROFILES: list[BaseProfile] = [
    GTAProfile(),
    ValorantProfile(),
    CS2Profile(),
    PUBGProfile(),
    SnowRunnerProfile(),
    ForzaProfile(),
    MinecraftProfile(),
    RocketLeagueProfile(),
]


def _normalize(text: str) -> str:
    return text.lower().replace("_", " ").replace("-", " ")


class ProfileRegistry:

    @classmethod
    def detect_profile(cls, filename: str) -> BaseProfile:
        stem = _normalize(Path(filename).stem)
        for profile in _PROFILES:
            for alias in profile.aliases:
                if alias in stem:
                    return profile
        return cls.get_default_profile()

    @classmethod
    def detect_profile_from_text(cls, text: str) -> BaseProfile:
        normalized = _normalize(text)
        for profile in _PROFILES:
            for alias in profile.aliases:
                if alias in normalized:
                    return profile
        return cls.get_default_profile()

    @classmethod
    def get_default_profile(cls) -> BaseProfile:
        return DefaultProfile()
