import unittest

from app.services.game_profiles.base_profile import DefaultProfile
from app.services.game_profiles.profile_registry import ProfileRegistry


class ProfileRegistryFilenameDetectionTests(unittest.TestCase):

    def test_gta_filename_detected(self):
        profile = ProfileRegistry.detect_profile("GTA_V_gameplay.mp4")
        self.assertEqual(profile.game_name, "Grand Theft Auto V")

    def test_valorant_filename_detected(self):
        profile = ProfileRegistry.detect_profile("Valorant_ranked_match.mp4")
        self.assertEqual(profile.game_name, "Valorant")

    def test_cs2_filename_detected(self):
        profile = ProfileRegistry.detect_profile("CS2_clutch.mp4")
        self.assertEqual(profile.game_name, "Counter-Strike 2")

    def test_pubg_filename_detected(self):
        profile = ProfileRegistry.detect_profile("PUBG_match.mp4")
        self.assertEqual(profile.game_name, "PUBG: Battlegrounds")

    def test_snowrunner_filename_detected(self):
        profile = ProfileRegistry.detect_profile("SnowRunner_gameplay.mkv")
        self.assertEqual(profile.game_name, "SnowRunner")

    def test_forza_filename_detected(self):
        profile = ProfileRegistry.detect_profile("Forza_Horizon_gameplay.mp4")
        self.assertEqual(profile.game_name, "Forza")

    def test_minecraft_filename_detected(self):
        profile = ProfileRegistry.detect_profile("Minecraft_survival.mp4")
        self.assertEqual(profile.game_name, "Minecraft")

    def test_rocket_league_filename_detected(self):
        profile = ProfileRegistry.detect_profile("Rocket_League_match.mp4")
        self.assertEqual(profile.game_name, "Rocket League")


class ProfileRegistryCaseAndNormalizationTests(unittest.TestCase):

    def test_uppercase_filename_detected(self):
        profile = ProfileRegistry.detect_profile("VALORANT_RANKED_MATCH.MP4")
        self.assertEqual(profile.game_name, "Valorant")

    def test_lowercase_filename_detected(self):
        profile = ProfileRegistry.detect_profile("valorant_ranked_match.mp4")
        self.assertEqual(profile.game_name, "Valorant")

    def test_mixed_case_filename_detected(self):
        profile = ProfileRegistry.detect_profile("cS2_ClUtCh_MoMeNt.mp4")
        self.assertEqual(profile.game_name, "Counter-Strike 2")

    def test_hyphen_separated_filename_detected(self):
        profile = ProfileRegistry.detect_profile("GTA-V-gameplay.mp4")
        self.assertEqual(profile.game_name, "Grand Theft Auto V")

    def test_space_separated_filename_detected(self):
        profile = ProfileRegistry.detect_profile("Rocket League match.mp4")
        self.assertEqual(profile.game_name, "Rocket League")

    def test_mixed_hyphen_and_underscore_filename_detected(self):
        profile = ProfileRegistry.detect_profile("snow-runner_gameplay.mkv")
        self.assertEqual(profile.game_name, "SnowRunner")


class ProfileRegistryTextDetectionTests(unittest.TestCase):

    def test_gta_text_detected(self):
        profile = ProfileRegistry.detect_profile_from_text(
            "an epic GTA heist gone wrong"
        )
        self.assertEqual(profile.game_name, "Grand Theft Auto V")

    def test_valorant_text_detected(self):
        profile = ProfileRegistry.detect_profile_from_text(
            "clutch Valorant ace to win the round"
        )
        self.assertEqual(profile.game_name, "Valorant")

    def test_cs2_text_detected(self):
        profile = ProfileRegistry.detect_profile_from_text(
            "insane CS2 headshot clip"
        )
        self.assertEqual(profile.game_name, "Counter-Strike 2")

    def test_snowrunner_text_detected(self):
        profile = ProfileRegistry.detect_profile_from_text(
            "SnowRunner truck stuck in the mud"
        )
        self.assertEqual(profile.game_name, "SnowRunner")

    def test_rocket_league_text_detected(self):
        profile = ProfileRegistry.detect_profile_from_text(
            "insane Rocket League aerial goal"
        )
        self.assertEqual(profile.game_name, "Rocket League")


class ProfileRegistryFallbackTests(unittest.TestCase):

    def test_unknown_filename_returns_default_profile(self):
        profile = ProfileRegistry.detect_profile("random_vacation_video.mp4")
        self.assertIsInstance(profile, DefaultProfile)
        self.assertEqual(profile.game_name, "Default")

    def test_unknown_text_returns_default_profile(self):
        profile = ProfileRegistry.detect_profile_from_text(
            "a completely unrelated description"
        )
        self.assertIsInstance(profile, DefaultProfile)
        self.assertEqual(profile.game_name, "Default")

    def test_empty_filename_returns_default_profile(self):
        profile = ProfileRegistry.detect_profile("")
        self.assertIsInstance(profile, DefaultProfile)
        self.assertEqual(profile.game_name, "Default")

    def test_empty_text_returns_default_profile(self):
        profile = ProfileRegistry.detect_profile_from_text("")
        self.assertIsInstance(profile, DefaultProfile)
        self.assertEqual(profile.game_name, "Default")

    def test_get_default_profile_returns_default_profile(self):
        profile = ProfileRegistry.get_default_profile()
        self.assertIsInstance(profile, DefaultProfile)


if __name__ == "__main__":
    unittest.main()
