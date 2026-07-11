"""
AGC-084: canonical backend explanation trace coverage.

ExplainabilityService.build() is the source of truth for `explanation.reasons`
surfaced to creators. These tests pin its deterministic behavior so scoring
changes elsewhere can't silently break the explanation without a test
failing here. Reasons are NEVER capped on the backend — that only happens
in the frontend presentation layer (see frontend/utils/highlightReasons.ts).
"""

import unittest
from unittest.mock import patch

from app.config.config import settings
from app.services.explainability_service import ExplainabilityService


class ExplainabilityServiceTests(unittest.TestCase):

    def setUp(self):
        # Pin synergy config so these tests don't depend on .env overrides.
        self._patchers = [
            patch.object(settings, "SYNERGY_ENABLED", True),
            patch.object(settings, "SYNERGY_SIGNAL_THRESHOLD", 0.50),
            patch.object(settings, "SYNERGY_INCREMENT", 0.10),
            patch.object(settings, "MAX_SYNERGY_MULTIPLIER", 1.50),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()

    def _build(self, **overrides):
        params = {
            "clip_score": 0.1,
            "motion_score": 0.1,
            "scene_score": 0.1,
            "audio_score": 0.1,
            "duration_score": 0.0,
            "weighted_score": 0.5,
            "ranking_score": 0.5,
            "adaptive_threshold": 0.20,
            "profile_name": "Default",
            "action": "idle moment",
            "category": "",
            "category_overrides": None,
            "profile_ranking_bonus": None,
        }
        params.update(overrides)
        return ExplainabilityService.build(**params)

    def test_all_signals_fire(self):
        result = self._build(
            clip_score=0.9,
            motion_score=0.9,
            scene_score=0.9,
            audio_score=0.9,
            action="intense combat encounter",
            category="combat",
            profile_ranking_bonus={"combat": 0.05},
        )

        self.assertEqual(
            result["reasons"],
            [
                "High CLIP confidence",
                "High motion",
                "Scene change detected",
                "Audio spike",
                "Category bonus applied",
                "Profile bonus applied",
                "Synergy activated",
            ],
        )
        self.assertGreater(result["category_multiplier"], 1.0)
        self.assertGreater(result["synergy_multiplier"], 1.0)

    def test_no_signals_fire(self):
        result = self._build(
            clip_score=0.1,
            motion_score=0.1,
            scene_score=0.1,
            audio_score=0.1,
            action="calm exploration moment",
            category="exploration",
            profile_ranking_bonus=None,
        )

        self.assertEqual(result["reasons"], [])
        self.assertLessEqual(result["category_multiplier"], 1.0)
        self.assertEqual(result["synergy_multiplier"], 1.0)

    def test_category_bonus_reason_fires_in_isolation(self):
        result = self._build(
            clip_score=0.1,
            motion_score=0.1,
            scene_score=0.1,
            audio_score=0.1,
            action="combat encounter",
            category="",
            profile_ranking_bonus=None,
        )

        self.assertEqual(result["reasons"], ["Category bonus applied"])
        self.assertEqual(result["category_multiplier"], 1.50)

    def test_profile_bonus_reason_fires_in_isolation(self):
        result = self._build(
            clip_score=0.1,
            motion_score=0.1,
            scene_score=0.1,
            audio_score=0.1,
            action="calm exploration moment",
            category="combat",
            profile_ranking_bonus={"combat": 0.05},
        )

        self.assertEqual(result["reasons"], ["Profile bonus applied"])

    def test_synergy_reason_fires_with_two_agreeing_signals(self):
        result = self._build(
            clip_score=0.6,
            motion_score=0.6,
            scene_score=0.1,
            audio_score=0.1,
            action="calm exploration moment",
            category="exploration",
            profile_ranking_bonus=None,
        )

        self.assertEqual(
            result["reasons"],
            ["High CLIP confidence", "High motion", "Synergy activated"],
        )
        # 2 strong signals -> 1 bonus signal -> 1.0 + 1 * SYNERGY_INCREMENT
        self.assertEqual(result["synergy_multiplier"], 1.10)

    def test_reasons_are_not_fabricated_beyond_four(self):
        """Backend must NOT cap reasons — capping is frontend-only (AGC-084)."""
        result = self._build(
            clip_score=0.9,
            motion_score=0.9,
            scene_score=0.9,
            audio_score=0.9,
            action="victory achieved",
            category="victory",
            profile_ranking_bonus={"victory": 0.02},
        )

        self.assertEqual(len(result["reasons"]), 7)


if __name__ == "__main__":
    unittest.main()
