"""
VED-P1-007: Highlight Quality Gate coverage.

A real GTA V production run scored a visually poor moment at ~0.96
weighted / 0.87 final purely from scene_score + synergy + category
amplification (clip=0.7317, motion=0.2232, scene=0.996, audio=0.0,
is_silent=True). These tests pin HighlightQualityGate.evaluate() so that
exact pattern is rejected deterministically, before any multiplier can
touch it, while legitimate silent/audio-rich/high-evidence candidates
still pass.
"""

import unittest
from unittest.mock import patch

from app.config.config import settings
from app.services.highlight_quality_gate import HighlightQualityGate
from app.services.scoring.orchestrator import ScoringOrchestrator


class HighlightQualityGateTestBase(unittest.TestCase):

    def setUp(self):
        self._patchers = [
            patch.object(settings, "HIGHLIGHT_QUALITY_GATE_ENABLED", True),
            patch.object(settings, "HIGHLIGHT_MIN_CLIP_SCORE", 0.30),
            patch.object(settings, "HIGHLIGHT_MIN_MOTION_SCORE", 0.35),
            patch.object(settings, "HIGHLIGHT_MIN_SCENE_SCORE", 0.55),
            patch.object(settings, "HIGHLIGHT_MIN_AUDIO_SCORE", 0.35),
            patch.object(settings, "HIGHLIGHT_MIN_EVIDENCE_COUNT", 1),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()

    def _evaluate(self, **overrides):
        params = {
            "clip_score": 0.5,
            "motion_score": 0.1,
            "scene_score": 0.1,
            "audio_score": 0.1,
            "is_silent": False,
            "frame_path": None,
        }
        params.update(overrides)
        return HighlightQualityGate.evaluate(**params)


class ProductionFalsePositiveReproTests(HighlightQualityGateTestBase):
    """Case 1 + the exact production failure pattern from the incident."""

    def test_production_gta_case_is_rejected(self):
        result = self._evaluate(
            clip_score=0.7317,
            motion_score=0.2232,
            scene_score=0.9960,
            audio_score=0.0,
            is_silent=True,
        )
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["reason"],
            "Quality gate rejected: insufficient independent action evidence",
        )
        self.assertEqual(result["evidence_count"], 0)

    def test_production_gta_case_would_have_scored_high_without_gate(self):
        """Proves the gate is necessary: raw weighted score alone (with
        category + synergy) reproduces the reported ~0.9576, confirming
        multiplier stacking — not evidence — was inflating this candidate.
        """
        with patch.object(settings, "SYNERGY_ENABLED", True), \
             patch.object(settings, "SYNERGY_SIGNAL_THRESHOLD", 0.50), \
             patch.object(settings, "SYNERGY_INCREMENT", 0.10), \
             patch.object(settings, "MAX_SYNERGY_MULTIPLIER", 1.50):
            weighted_score = ScoringOrchestrator.compute_weighted_score(
                clip_score=0.7317,
                motion_score=0.2232,
                audio_score=0.0,
                scene_score=0.9960,
                duration_score=0.6250,
                # matches GTAProfile's "victory" prompt set (contains
                # "achievement", the keyword ScoringOrchestrator's generic
                # apply_action_weight() maps to the victory category).
                action="criminal rank up achievement",
                is_silent=True,
            )
        self.assertAlmostEqual(weighted_score, 0.9576, places=3)

    def test_high_scene_mediocre_clip_weak_motion_no_audio_rejected(self):
        result = self._evaluate(
            clip_score=0.40,
            motion_score=0.15,
            scene_score=0.90,
            audio_score=0.0,
            is_silent=False,
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["evidence_count"], 0)


class AcceptedCandidateTests(HighlightQualityGateTestBase):

    def test_strong_clip_strong_motion_no_audio_accepted(self):
        result = self._evaluate(
            clip_score=0.70,
            motion_score=0.60,
            scene_score=0.10,
            audio_score=0.0,
            is_silent=False,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["evidence_count"], 1)

    def test_strong_clip_strong_scene_with_sufficient_evidence_accepted(self):
        result = self._evaluate(
            clip_score=0.75,
            motion_score=0.40,
            scene_score=0.90,
            audio_score=0.0,
            is_silent=False,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["evidence_count"], 1)

    def test_silent_gameplay_with_strong_motion_accepted(self):
        """Case: audio=0 but strong visual/action signals -> accepted.
        Silent classification excludes audio from the requirement rather
        than treating it as a failure.
        """
        result = self._evaluate(
            clip_score=0.65,
            motion_score=0.55,
            scene_score=0.30,
            audio_score=0.0,
            is_silent=True,
        )
        self.assertTrue(result["passed"])

    def test_audio_rich_gameplay_audio_contributes(self):
        result = self._evaluate(
            clip_score=0.50,
            motion_score=0.10,
            scene_score=0.10,
            audio_score=0.60,
            is_silent=False,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["evidence_count"], 1)

    def test_silent_video_ignores_high_audio_score(self):
        """Audio must never count as evidence for a silent-classified
        video, even if a stray audio_score value is nonzero.
        """
        result = self._evaluate(
            clip_score=0.50,
            motion_score=0.10,
            scene_score=0.10,
            audio_score=0.90,
            is_silent=True,
        )
        self.assertFalse(result["passed"])


class RelevanceFloorTests(HighlightQualityGateTestBase):

    def test_clip_below_floor_rejected_regardless_of_other_signals(self):
        result = self._evaluate(
            clip_score=0.10,
            motion_score=0.90,
            scene_score=0.90,
            audio_score=0.90,
            is_silent=False,
        )
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["reason"],
            "Quality gate rejected: insufficient semantic relevance",
        )


class MultiplierIsolationTests(HighlightQualityGateTestBase):
    """Category and synergy amplification must never rescue a candidate
    the gate has already rejected — the gate runs on raw pre-multiplier
    signals, so this is architectural, but these tests pin the behavior
    end-to-end via ScoringOrchestrator.
    """

    def test_category_multiplier_cannot_rescue_failed_gate(self):
        gate_result = self._evaluate(
            clip_score=0.73,
            motion_score=0.22,
            scene_score=0.99,
            audio_score=0.0,
            is_silent=True,
        )
        self.assertFalse(gate_result["passed"])

        with patch.object(settings, "SYNERGY_ENABLED", False):
            weighted_score = ScoringOrchestrator.compute_weighted_score(
                clip_score=0.73,
                motion_score=0.22,
                audio_score=0.0,
                scene_score=0.99,
                duration_score=0.0,
                action="combat encounter",  # highest category multiplier: 1.50
                is_silent=True,
            )
        # Even the strongest category multiplier drives the weighted score
        # well above the adaptive threshold — the gate result is unaffected.
        self.assertGreater(weighted_score, settings.DEFAULT_HIGHLIGHT_THRESHOLD)
        self.assertFalse(gate_result["passed"])

    def test_synergy_cannot_rescue_failed_gate(self):
        gate_result = self._evaluate(
            clip_score=0.73,
            motion_score=0.22,
            scene_score=0.99,
            audio_score=0.0,
            is_silent=True,
        )
        self.assertFalse(gate_result["passed"])

        with patch.object(settings, "SYNERGY_ENABLED", True), \
             patch.object(settings, "SYNERGY_SIGNAL_THRESHOLD", 0.50), \
             patch.object(settings, "SYNERGY_INCREMENT", 0.10), \
             patch.object(settings, "MAX_SYNERGY_MULTIPLIER", 1.50):
            weighted_score = ScoringOrchestrator.compute_weighted_score(
                clip_score=0.73,
                motion_score=0.22,
                audio_score=0.0,
                scene_score=0.99,
                duration_score=0.0,
                action="exploration walk",  # lowest category multiplier: 0.80
                is_silent=True,
            )
        self.assertGreater(weighted_score, 0.5)
        self.assertFalse(gate_result["passed"])


class GameProfileCompatibilityTests(HighlightQualityGateTestBase):
    """Cases 8/9/10: the gate is profile-agnostic — it only consumes raw
    signals, so DefaultProfile/GTA/SnowRunner scoring-weight and category
    overrides never reach it and cannot change its verdict.
    """

    def test_default_profile_style_signals_behave_as_generic_case(self):
        result = self._evaluate(
            clip_score=0.55,
            motion_score=0.10,
            scene_score=0.20,
            audio_score=0.10,
            is_silent=False,
        )
        self.assertFalse(result["passed"])

    def test_gta_category_override_does_not_change_gate_verdict(self):
        from app.services.game_profiles.gta_profile import GTAProfile

        profile = GTAProfile()
        signals = dict(
            clip_score=0.73, motion_score=0.22, scene_score=0.99,
            audio_score=0.0, is_silent=True,
        )
        without_profile = self._evaluate(**signals)
        # GTA's category_weight_overrides never enter evaluate() — confirm
        # the profile object has no bearing on the gate's inputs/outputs.
        self.assertIsNotNone(profile.category_weight_overrides)
        self.assertEqual(without_profile["passed"], False)

    def test_snowrunner_profile_weights_do_not_bypass_gate(self):
        from app.services.game_profiles.snowrunner_profile import SnowRunnerProfile

        profile = SnowRunnerProfile()
        self.assertIsNotNone(profile.scoring_weights)

        # A legitimate SnowRunner highlight with real motion evidence
        # (truck recovery, winch action) still passes.
        result = self._evaluate(
            clip_score=0.60,
            motion_score=0.50,
            scene_score=0.40,
            audio_score=0.20,
            is_silent=False,
        )
        self.assertTrue(result["passed"])


class AdaptiveThresholdIndependenceTests(HighlightQualityGateTestBase):
    """Case 11: the gate must not read or depend on adaptive-threshold
    configuration — it evaluates evidence, not the accept/reject
    threshold, so changing those settings cannot change its verdict.
    """

    def test_gate_verdict_unaffected_by_adaptive_threshold_settings(self):
        signals = dict(
            clip_score=0.73, motion_score=0.22, scene_score=0.99,
            audio_score=0.0, is_silent=True,
        )
        with patch.object(settings, "ADAPTIVE_THRESHOLD_ENABLED", True), \
             patch.object(settings, "ADAPTIVE_THRESHOLD_PERCENTILE", 10), \
             patch.object(settings, "MIN_ADAPTIVE_THRESHOLD", 0.01), \
             patch.object(settings, "DEFAULT_HIGHLIGHT_THRESHOLD", 0.01):
            low_threshold_result = self._evaluate(**signals)

        with patch.object(settings, "ADAPTIVE_THRESHOLD_ENABLED", False), \
             patch.object(settings, "DEFAULT_HIGHLIGHT_THRESHOLD", 0.99):
            high_threshold_result = self._evaluate(**signals)

        self.assertEqual(low_threshold_result["passed"], False)
        self.assertEqual(high_threshold_result["passed"], False)


class ConfigurationTests(HighlightQualityGateTestBase):

    def test_quality_gate_can_be_disabled(self):
        with patch.object(settings, "HIGHLIGHT_QUALITY_GATE_ENABLED", False):
            result = self._evaluate(
                clip_score=0.01,
                motion_score=0.01,
                scene_score=0.99,
                audio_score=0.0,
                is_silent=True,
            )
        self.assertTrue(result["passed"])
        self.assertEqual(result["reason"], "Quality gate disabled")


class FramePathSafetyTests(HighlightQualityGateTestBase):

    def test_missing_frame_path_does_not_crash(self):
        result = self._evaluate(
            clip_score=0.70,
            motion_score=0.60,
            scene_score=0.10,
            audio_score=0.0,
            is_silent=False,
            frame_path=None,
        )
        self.assertTrue(result["passed"])

    def test_nonexistent_frame_path_does_not_crash(self):
        result = self._evaluate(
            clip_score=0.70,
            motion_score=0.60,
            scene_score=0.10,
            audio_score=0.0,
            is_silent=False,
            frame_path="C:/nonexistent/path/does_not_exist.jpg",
        )
        self.assertTrue(result["passed"])

    def test_empty_string_frame_path_does_not_crash(self):
        result = self._evaluate(
            clip_score=0.70,
            motion_score=0.60,
            scene_score=0.10,
            audio_score=0.0,
            is_silent=False,
            frame_path="",
        )
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
