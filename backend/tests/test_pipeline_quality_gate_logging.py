"""
VED-P1-008: quality-gate rejection observability.

Before this change, pipeline_service.py's two quality-gate rejection
branches (coarse pass and fine pass) only emitted a bare print() —
nothing reached LoggerService or the job result, so an operator could
not tell a quality-gate rejection apart from an adaptive-threshold
rejection, a candidate that was never selected, or a pipeline failure.

These tests pin:
  A) the new logging helper emits job_id, frame timestamp, rejection
     reason, and the raw signal values (clip/motion/scene/audio/
     duration scores, is_silent, evidence_count, quality_score);
  B) both the coarse-pass and fine-pass rejection branches invoke it;
  C) the candidate is still rejected (no highlight is produced) —
     i.e. logging is additive, not a new acceptance path;
  D) HighlightQualityGate's own logic is untouched — the exact
     production false-positive signal pattern from
     test_highlight_quality_gate.py is still rejected under real
     (unpatched) gate settings, purely via the existing gate branches.
"""

import unittest
from unittest.mock import patch, MagicMock

from app.config.config import settings
from app.services.pipeline_service import PipelineService
from app.services.profiler_service import PipelineProfiler


class LogQualityGateRejectionHelperTests(unittest.TestCase):
    """Direct unit tests of the new PipelineService._log_quality_gate_rejection
    helper — the single seam both rejection branches call through."""

    def _scores(self, **overrides):
        base = {
            "clip_score": 0.7317,
            "motion_score": 0.2232,
            "scene_score": 0.9960,
            "audio_score": 0.0,
            "duration_score": 0.6250,
            "quality_gate": {
                "passed": False,
                "reason": "Quality gate rejected: insufficient independent action evidence",
                "evidence_count": 0,
                "quality_score": 0.7451,
            },
        }
        base.update(overrides)
        return base

    @patch("app.services.pipeline_service.LoggerService")
    def test_coarse_rejection_logs_all_required_fields(self, mock_logger):
        frame = {"timestamp_second": 42.5, "frame_name": "frame_0042.jpg"}
        scores = self._scores()

        PipelineService._log_quality_gate_rejection(
            frame=frame,
            scores=scores,
            is_silent=True,
            job_id="job-123",
            scan_pass="coarse",
        )

        mock_logger.info.assert_called_once()
        args, kwargs = mock_logger.info.call_args
        message = args[0]

        self.assertEqual(kwargs.get("job_id"), "job-123")
        self.assertIn("event=quality_gate_rejected", message)
        self.assertIn("pass=coarse", message)
        self.assertIn("timestamp=42.5", message)
        self.assertIn(
            "reason=Quality gate rejected: insufficient independent action evidence",
            message,
        )
        self.assertIn("evidence_count=0", message)
        self.assertIn("quality_score=0.7451", message)
        self.assertIn("clip_score=0.7317", message)
        self.assertIn("motion_score=0.2232", message)
        self.assertIn("scene_score=0.996", message)
        self.assertIn("audio_score=0.0", message)
        self.assertIn("duration_score=0.625", message)
        self.assertIn("is_silent=True", message)

        # No file paths or frame image contents are logged.
        self.assertNotIn("frame_0042.jpg", message)

    @patch("app.services.pipeline_service.LoggerService")
    def test_fine_rejection_logs_fine_pass_label(self, mock_logger):
        frame = {"timestamp_second": 7.0, "frame_name": "frame_0007.jpg"}
        scores = self._scores(
            quality_gate={
                "passed": False,
                "reason": "Quality gate rejected: insufficient semantic relevance",
                "evidence_count": 0,
                "quality_score": 0.1,
            }
        )

        PipelineService._log_quality_gate_rejection(
            frame=frame,
            scores=scores,
            is_silent=False,
            job_id=None,
            scan_pass="fine",
        )

        mock_logger.info.assert_called_once()
        args, kwargs = mock_logger.info.call_args
        message = args[0]

        self.assertIsNone(kwargs.get("job_id"))
        self.assertIn("pass=fine", message)
        self.assertIn("reason=Quality gate rejected: insufficient semantic relevance", message)
        self.assertIn("is_silent=False", message)

    @patch("app.services.pipeline_service.LoggerService")
    def test_helper_has_no_return_value_and_does_not_mutate_scores(self, mock_logger):
        """The helper is a pure side-effecting logger — it must not be able
        to influence candidate selection (it has nothing to return and must
        not mutate the scores/quality_gate dict it was given)."""
        frame = {"timestamp_second": 1.0, "frame_name": "f.jpg"}
        scores = self._scores()
        before = dict(scores["quality_gate"])

        result = PipelineService._log_quality_gate_rejection(
            frame=frame,
            scores=scores,
            is_silent=True,
            job_id="job-x",
            scan_pass="coarse",
        )

        self.assertIsNone(result)
        self.assertEqual(scores["quality_gate"], before)


class RunPipelineQualityGateRejectionIntegrationTests(unittest.TestCase):
    """Drives the real _run_pipeline coarse+fine scan loops (unmocked
    control flow, unmocked HighlightQualityGate) with the exact production
    false-positive signal pattern, to confirm both rejection branches are
    reached in situ and that rejection still means "no highlight produced."
    """

    def _frames(self, count):
        return [
            {"frame_name": f"frame_{i}.jpg", "timestamp_second": float(i)}
            for i in range(count)
        ]

    @patch("app.services.pipeline_service.LoggerService")
    @patch("app.services.pipeline_service.ProgressService.update")
    @patch("app.services.pipeline_service.ScoringOrchestrator.compute_weighted_score")
    @patch("app.services.pipeline_service.DurationScorer.score")
    @patch("app.services.pipeline_service.ClipScorer.score")
    @patch("app.services.pipeline_service.AudioScorer.score")
    @patch("app.services.pipeline_service.SceneScorer.score")
    @patch("app.services.pipeline_service.MotionScorer.score")
    @patch("app.services.pipeline_service.ClipService.get_highlight_result")
    @patch("app.services.pipeline_service.AudioService.build_audio_map")
    def test_coarse_and_fine_rejections_produce_no_highlight(
        self,
        mock_build_audio_map,
        mock_clip_service,
        mock_motion,
        mock_scene,
        mock_audio,
        mock_clip_scorer,
        mock_duration,
        mock_weighted_score,
        mock_progress_update,
        mock_logger,
    ):
        # Exact production false-positive pattern (see
        # test_highlight_quality_gate.py::ProductionFalsePositiveReproTests)
        # — deterministically rejected by the real, unpatched gate defaults
        # (HIGHLIGHT_MIN_CLIP_SCORE=0.30, HIGHLIGHT_MIN_MOTION_SCORE=0.35,
        # HIGHLIGHT_MIN_EVIDENCE_COUNT=1): clip clears the relevance floor,
        # but silent + weak motion means zero independent evidence.
        mock_build_audio_map.return_value = {"audio_map": {}, "is_silent": True}
        mock_clip_service.return_value = {
            "best_match": "combat encounter",
            "category": "combat",
            "is_highlight": True,
        }
        mock_motion.return_value = 0.2232
        mock_scene.return_value = 0.9960
        mock_audio.return_value = 0.0
        mock_clip_scorer.return_value = 0.7317
        mock_duration.return_value = 0.6250
        # Comfortably above both the coarse trigger and the (disabled-
        # adaptive, default) DEFAULT_HIGHLIGHT_THRESHOLD, so every scored
        # frame is evaluated as a highlight candidate and only the quality
        # gate stands between it and acceptance.
        mock_weighted_score.return_value = 0.95

        profiler = PipelineProfiler()

        with patch.object(settings, "ADAPTIVE_THRESHOLD_ENABLED", False):
            result = PipelineService._run_pipeline(
                video_path="C:/fake/video.mp4",
                job_id=None,
                storage_job_id="test-storage-job",
                user_id=None,
                frames_data={
                    "frames": self._frames(3),
                    "frame_location": "C:/fake/frames",
                    "duration": 3.0,
                },
                start_time=0.0,
                profiler=profiler,
                profile=None,
            )

        # C) still rejected: zero highlights survive, so _run_pipeline takes
        # the empty-metadata early return rather than producing a highlight.
        self.assertEqual(result.get("highlights_found"), 0)
        self.assertEqual(result.get("all_highlights"), [])

        # A/B) both the coarse-pass frame (index 0) and the fine-pass frames
        # (indices 1, 2, opened into the fine-scan window by index 0's
        # candidate window) were logged as quality-gate rejections.
        logged_messages = [
            call.args[0] for call in mock_logger.info.call_args_list
        ]
        gate_rejection_messages = [
            m for m in logged_messages if "event=quality_gate_rejected" in m
        ]
        self.assertGreaterEqual(len(gate_rejection_messages), 2)
        self.assertTrue(
            any("pass=coarse" in m for m in gate_rejection_messages)
        )
        self.assertTrue(
            any("pass=fine" in m for m in gate_rejection_messages)
        )
        for message in gate_rejection_messages:
            self.assertIn(
                "reason=Quality gate rejected: insufficient independent action evidence",
                message,
            )
            self.assertIn("evidence_count=0", message)


if __name__ == "__main__":
    unittest.main()
