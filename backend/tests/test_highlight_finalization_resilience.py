"""
VED-P1-009: partial highlight finalization failure resilience.

Before this change, PipelineService._run_pipeline finalized every ranked
highlight in a single unguarded loop (_finalize_highlight_clip called with
no try/except). A single highlight's FFmpeg/thumbnail failure propagated
all the way to BackgroundJobService.run_pipeline, discarding every already
-finalized sibling highlight and failing the whole job (see the VED-P1-009
resilience audit's F2 finding).

This adds PipelineService._finalize_highlights, which isolates each
highlight's finalization: a failure is logged and the highlight dropped;
siblings continue. If every highlight fails, a controlled RuntimeError is
raised so the job still reaches BackgroundJobService's existing fail_job +
credit-refund path (CTO decision: the all-fail case must remain a FAILED
job with a refund; partial success must COMPLETE using only the
highlights that finalized).

These tests pin, in three layers:
  A) FinalizeHighlightsUnitTests — the isolation/ordering/exception
     contract of _finalize_highlights directly (fast, precise).
  B) RunPipelineFinalizationIntegrationTests — the real _run_pipeline
     control flow, proving only successfully finalized highlights ever
     reach ReelService.merge_clips / build_metadata / stats.
  C) BackgroundJobServiceCreditBehaviorTests — the existing (unmodified)
     BackgroundJobService.run_pipeline credit-refund path is reached for
     the all-fail case and NOT reached for a completed (partial or full)
     job.
"""

import unittest
from contextlib import ExitStack
from unittest.mock import patch, MagicMock

from app.config.config import settings
from app.services.pipeline_service import PipelineService
from app.services.profiler_service import PipelineProfiler


# ---------------------------------------------------------------------------
# A) Direct unit tests of PipelineService._finalize_highlights /
#    _log_highlight_finalization_failure
# ---------------------------------------------------------------------------

class FinalizeHighlightsUnitTests(unittest.TestCase):

    def _highlight(self, timestamp, weighted_score=0.9):
        return {
            "timestamp": timestamp,
            "category": "combat",
            "action": "combat encounter",
            "weighted_score": weighted_score,
            "duration": 8,
        }

    def test_partial_failure_isolates_and_preserves_order(self):
        """A succeeds, B raises, C succeeds -> [A, C], in that order."""
        a = self._highlight(10.0)
        b = self._highlight(60.0)
        c = self._highlight(110.0)

        def fake_finalize(video_path, highlight, profiler, storage_job_id):
            if highlight is b:
                raise Exception("Clip creation failed: simulated ffmpeg failure")
            highlight["clip_path"] = f"clips/{highlight['timestamp']}.mp4"
            return highlight

        with patch.object(
            PipelineService, "_finalize_highlight_clip", side_effect=fake_finalize
        ), patch("app.services.pipeline_service.LoggerService") as mock_logger:
            result = PipelineService._finalize_highlights(
                video_path="video.mp4",
                top_highlights=[a, b, c],
                profiler=PipelineProfiler(),
                storage_job_id="job-storage-1",
                job_id="job-1",
            )

        self.assertEqual(result, [a, c])
        self.assertNotIn(b, result)
        mock_logger.error.assert_called_once()

    def test_all_failure_raises_controlled_exception(self):
        """Every highlight fails -> a controlled RuntimeError, not a raw
        FFmpeg exception and not a normal empty-list return."""
        a = self._highlight(10.0)
        b = self._highlight(60.0)
        c = self._highlight(110.0)

        def always_fail(video_path, highlight, profiler, storage_job_id):
            raise Exception(f"Clip creation failed: ffmpeg stderr for {highlight['timestamp']}")

        with patch.object(
            PipelineService, "_finalize_highlight_clip", side_effect=always_fail
        ), patch("app.services.pipeline_service.LoggerService") as mock_logger:
            with self.assertRaises(RuntimeError) as ctx:
                PipelineService._finalize_highlights(
                    video_path="video.mp4",
                    top_highlights=[a, b, c],
                    profiler=PipelineProfiler(),
                    storage_job_id="job-storage-1",
                    job_id="job-1",
                )

        self.assertEqual(
            str(ctx.exception),
            "All selected highlights failed during clip finalization.",
        )
        # No raw ffmpeg internals leaked into the controlled exception's
        # user/DB-facing message.
        self.assertNotIn("ffmpeg stderr", str(ctx.exception))
        self.assertEqual(mock_logger.error.call_count, 3)

    def test_happy_path_all_succeed_preserves_list(self):
        """No failures -> identical list, identical order, nothing dropped."""
        a = self._highlight(10.0)
        b = self._highlight(60.0)
        c = self._highlight(110.0)

        def always_succeed(video_path, highlight, profiler, storage_job_id):
            highlight["clip_path"] = f"clips/{highlight['timestamp']}.mp4"
            return highlight

        with patch.object(
            PipelineService, "_finalize_highlight_clip", side_effect=always_succeed
        ), patch("app.services.pipeline_service.LoggerService") as mock_logger:
            result = PipelineService._finalize_highlights(
                video_path="video.mp4",
                top_highlights=[a, b, c],
                profiler=PipelineProfiler(),
                storage_job_id="job-storage-1",
                job_id="job-1",
            )

        self.assertEqual(result, [a, b, c])
        mock_logger.error.assert_not_called()

    def test_single_success_out_of_three(self):
        """A and B fail, only C survives -> a one-item list, not empty."""
        a = self._highlight(10.0)
        b = self._highlight(60.0)
        c = self._highlight(110.0)

        def fake_finalize(video_path, highlight, profiler, storage_job_id):
            if highlight is c:
                highlight["clip_path"] = "clips/110.0.mp4"
                return highlight
            raise Exception("Clip creation failed: simulated ffmpeg failure")

        with patch.object(
            PipelineService, "_finalize_highlight_clip", side_effect=fake_finalize
        ), patch("app.services.pipeline_service.LoggerService"):
            result = PipelineService._finalize_highlights(
                video_path="video.mp4",
                top_highlights=[a, b, c],
                profiler=PipelineProfiler(),
                storage_job_id="job-storage-1",
                job_id="job-1",
            )

        self.assertEqual(result, [c])

    def test_failure_logging_fields_and_no_unnecessary_leakage(self):
        """Structured error log carries the event id, job_id and the
        failed highlight's timestamp, and does not gratuitously embed
        clip/thumbnail file paths (which don't exist for a failed
        highlight in the first place)."""
        highlight = self._highlight(42.5)
        error = Exception("Clip creation failed: ffmpeg non-zero exit")

        with patch("app.services.pipeline_service.LoggerService") as mock_logger:
            result = PipelineService._log_highlight_finalization_failure(
                highlight=highlight,
                error=error,
                job_id="job-abc",
            )

        self.assertIsNone(result)
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        message = args[0]

        self.assertEqual(kwargs.get("job_id"), "job-abc")
        self.assertIn("event=highlight_finalization_failed", message)
        self.assertIn("timestamp=42.5", message)
        self.assertIn("error=Clip creation failed: ffmpeg non-zero exit", message)
        self.assertNotIn("clip_path", message)
        self.assertNotIn("thumbnail_path", message)


# ---------------------------------------------------------------------------
# B) Integration tests driving the real _run_pipeline control flow
# ---------------------------------------------------------------------------

class RunPipelineFinalizationIntegrationTests(unittest.TestCase):
    """Drives _run_pipeline with the frame-scoring stack mocked to
    deterministically accept exactly three well-separated, distinct-action
    candidates (distinct actions so HighlightRankingService.MAX_PER_ACTION
    doesn't collapse them), and only _finalize_highlight_clip mocked to
    control which highlights succeed/fail. Everything from ReelService
    onward is mocked to observe exactly what the reel/result pipeline
    receives.
    """

    # index 0 never gets a real motion/scene/audio score (_score_single_frame
    # skips those for the very first frame), so it can never clear the
    # quality gate — it's given a dedicated is_highlight=False response and
    # excluded from the three real candidates, which start at index 5.
    WARMUP_ACTION = ("warmup frame", "warmup")
    ACTIONS = [
        ("combat encounter", "combat"),
        ("epic stunt jump", "stunt"),
        ("victory celebration", "victory"),
    ]

    def _frames(self, count):
        # 20s apart so the three coarse-scan hits (indices 5, 10, 15) land
        # 100s apart (> HighlightRankingService.MIN_TIMESTAMP_GAP=45s and
        # far outside FINE_SCAN_WINDOW_SECONDS), and no fine-scan frame
        # falls inside another candidate's window.
        return [
            {"frame_name": f"frame_{i}.jpg", "timestamp_second": float(i * 20)}
            for i in range(count)
        ]

    def _clip_service_side_effect(self):
        return [
            {"best_match": self.WARMUP_ACTION[0], "category": self.WARMUP_ACTION[1], "is_highlight": False}
        ] + [
            {"best_match": action, "category": category, "is_highlight": True}
            for action, category in self.ACTIONS
        ]

    def _run(self, finalize_side_effect):
        stack = ExitStack()
        mocks = {}

        def add(target, **kwargs):
            return stack.enter_context(patch(target, **kwargs))

        add("app.services.pipeline_service.LoggerService")
        add("app.services.pipeline_service.ProgressService.update")
        add(
            "app.services.pipeline_service.AudioService.build_audio_map",
            return_value={"audio_map": {}, "is_silent": False},
        )
        add(
            "app.services.pipeline_service.ClipService.get_highlight_result",
            side_effect=self._clip_service_side_effect(),
        )
        add("app.services.pipeline_service.MotionScorer.score", return_value=0.5)
        add("app.services.pipeline_service.SceneScorer.score", return_value=0.9)
        add("app.services.pipeline_service.AudioScorer.score", return_value=0.5)
        add("app.services.pipeline_service.ClipScorer.score", return_value=0.8)
        add("app.services.pipeline_service.DurationScorer.score", return_value=0.6)
        add(
            "app.services.pipeline_service.ScoringOrchestrator.compute_weighted_score",
            return_value=0.95,
        )
        add(
            "app.services.pipeline_service.PipelineService._finalize_highlight_clip",
            side_effect=finalize_side_effect,
        )
        mocks["reel"] = add(
            "app.services.pipeline_service.ReelService.merge_clips",
            return_value={
                "final_video": "reels/final.mp4",
                "vertical_video": "reels/final_vertical.mp4",
                "reel_generation_seconds": 1.0,
                "vertical_reel_seconds": 1.0,
            },
        )
        add(
            "app.services.pipeline_service.TitleService.generate_title",
            return_value="Test Title",
        )
        add(
            "app.services.pipeline_service.ViralPackageService.generate_package",
            return_value={"description": "desc", "hashtags": ["#test"]},
        )
        add(
            "app.services.pipeline_service.WhisperService.transcribe_video",
            return_value={"text": "hello world", "language": "en", "segments": []},
        )
        add(
            "app.services.pipeline_service.CaptionService.add_captions",
            return_value="reels/captioned.mp4",
        )
        add(
            "app.services.pipeline_service.ResultExportService.save_result",
            return_value="results/result.json",
        )

        with stack:
            with patch.object(settings, "ADAPTIVE_THRESHOLD_ENABLED", False):
                result = PipelineService._run_pipeline(
                    video_path="C:/fake/video.mp4",
                    job_id=None,
                    storage_job_id="test-storage-job",
                    user_id=None,
                    frames_data={
                        "frames": self._frames(16),
                        "frame_location": "C:/fake/frames",
                        "duration": 320.0,
                    },
                    start_time=0.0,
                    profiler=PipelineProfiler(),
                    profile=None,
                )

        return result, mocks

    def _succeed(self, highlight):
        slug = highlight["action"].replace(" ", "_")
        highlight["score"] = highlight["weighted_score"]
        highlight["thumbnail_score"] = 0.5
        highlight["clip_path"] = f"clips/{slug}.mp4"
        highlight["thumbnail_path"] = f"thumbnails/{slug}.jpg"
        return highlight

    def test_partial_failure_reel_and_result_receive_only_successful_highlights(self):
        """A) 3 selected, B ('epic stunt jump') fails -> job completes,
        reel and result contain exactly A and C, in order."""

        def finalize_side_effect(video_path, highlight, profiler, storage_job_id):
            if highlight["action"] == "epic stunt jump":
                raise Exception("Clip creation failed: simulated ffmpeg non-zero exit")
            return self._succeed(highlight)

        result, mocks = self._run(finalize_side_effect)

        self.assertEqual(result["highlights_found"], 2)
        surviving_actions = [h["action"] for h in result["all_highlights"]]
        self.assertEqual(
            surviving_actions, ["combat encounter", "victory celebration"]
        )

        mocks["reel"].assert_called_once()
        clip_paths_arg = mocks["reel"].call_args.args[0]
        self.assertEqual(
            clip_paths_arg,
            ["clips/combat_encounter.mp4", "clips/victory_celebration.mp4"],
        )

    def test_all_failure_raises_and_never_reaches_reel_generation(self):
        """B) all 3 fail -> RuntimeError propagates out of _run_pipeline,
        ReelService.merge_clips is never invoked, no reel/result exists."""

        def always_fail(video_path, highlight, profiler, storage_job_id):
            raise Exception(f"Clip creation failed: {highlight['action']}")

        stack = ExitStack()

        def add(target, **kwargs):
            return stack.enter_context(patch(target, **kwargs))

        add("app.services.pipeline_service.LoggerService")
        add("app.services.pipeline_service.ProgressService.update")
        add(
            "app.services.pipeline_service.AudioService.build_audio_map",
            return_value={"audio_map": {}, "is_silent": False},
        )
        add(
            "app.services.pipeline_service.ClipService.get_highlight_result",
            side_effect=self._clip_service_side_effect(),
        )
        add("app.services.pipeline_service.MotionScorer.score", return_value=0.5)
        add("app.services.pipeline_service.SceneScorer.score", return_value=0.9)
        add("app.services.pipeline_service.AudioScorer.score", return_value=0.5)
        add("app.services.pipeline_service.ClipScorer.score", return_value=0.8)
        add("app.services.pipeline_service.DurationScorer.score", return_value=0.6)
        add(
            "app.services.pipeline_service.ScoringOrchestrator.compute_weighted_score",
            return_value=0.95,
        )
        add(
            "app.services.pipeline_service.PipelineService._finalize_highlight_clip",
            side_effect=always_fail,
        )
        mock_reel = add("app.services.pipeline_service.ReelService.merge_clips")

        with stack:
            with patch.object(settings, "ADAPTIVE_THRESHOLD_ENABLED", False):
                with self.assertRaises(RuntimeError) as ctx:
                    PipelineService._run_pipeline(
                        video_path="C:/fake/video.mp4",
                        job_id=None,
                        storage_job_id="test-storage-job",
                        user_id=None,
                        frames_data={
                            "frames": self._frames(16),
                            "frame_location": "C:/fake/frames",
                            "duration": 320.0,
                        },
                        start_time=0.0,
                        profiler=PipelineProfiler(),
                        profile=None,
                    )

        self.assertEqual(
            str(ctx.exception),
            "All selected highlights failed during clip finalization.",
        )
        mock_reel.assert_not_called()

    def test_happy_path_unchanged_when_all_finalize_successfully(self):
        """C) no failures -> all three highlights survive, in ranked
        order, reel receives all three clip paths."""

        def finalize_side_effect(video_path, highlight, profiler, storage_job_id):
            return self._succeed(highlight)

        result, mocks = self._run(finalize_side_effect)

        self.assertEqual(result["highlights_found"], 3)
        surviving_actions = [h["action"] for h in result["all_highlights"]]
        self.assertEqual(
            surviving_actions,
            ["combat encounter", "epic stunt jump", "victory celebration"],
        )
        mocks["reel"].assert_called_once()
        clip_paths_arg = mocks["reel"].call_args.args[0]
        self.assertEqual(
            clip_paths_arg,
            [
                "clips/combat_encounter.mp4",
                "clips/epic_stunt_jump.mp4",
                "clips/victory_celebration.mp4",
            ],
        )

    def test_single_success_reel_receives_exactly_one_clip(self):
        """F) A and B fail, only C ('victory celebration') survives ->
        job completes with exactly one highlight, reel receives one clip."""

        def finalize_side_effect(video_path, highlight, profiler, storage_job_id):
            if highlight["action"] != "victory celebration":
                raise Exception("Clip creation failed: simulated ffmpeg non-zero exit")
            return self._succeed(highlight)

        result, mocks = self._run(finalize_side_effect)

        self.assertEqual(result["highlights_found"], 1)
        self.assertEqual(
            [h["action"] for h in result["all_highlights"]],
            ["victory celebration"],
        )
        mocks["reel"].assert_called_once()
        clip_paths_arg = mocks["reel"].call_args.args[0]
        self.assertEqual(clip_paths_arg, ["clips/victory_celebration.mp4"])


# ---------------------------------------------------------------------------
# C) BackgroundJobService credit-refund behavior (existing, unmodified code)
# ---------------------------------------------------------------------------

class BackgroundJobServiceCreditBehaviorTests(unittest.TestCase):
    """Confirms PipelineService's new controlled all-fail exception is
    routed through BackgroundJobService.run_pipeline's EXISTING except
    block (fail_job + refund_credit), and that a completed job (full or
    partial success) never triggers a refund. No BackgroundJobService
    code is changed by VED-P1-009 — these tests only pin that the
    existing behavior is reached correctly given the new exception.
    """

    def test_all_fail_exception_triggers_fail_job_and_refund(self):
        from app.services.background_job_service import BackgroundJobService

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            side_effect=RuntimeError(
                "All selected highlights failed during clip finalization."
            ),
        ), patch(
            "app.services.background_job_service.JobService"
        ) as mock_job_service, patch(
            "app.services.background_job_service.SubscriptionService.is_pro_active",
            return_value=False,
        ), patch(
            "app.services.background_job_service.AuthService"
        ) as mock_auth_service, patch(
            "app.services.background_job_service.CleanupService"
        ), patch(
            "app.services.background_job_service.LoggerService"
        ):
            BackgroundJobService.run_pipeline(
                job_id="job-1", video_path="video.mp4", user_id=7
            )

        mock_job_service.fail_job.assert_called_once()
        self.assertEqual(mock_job_service.fail_job.call_args.kwargs["job_id"], "job-1")
        self.assertIn(
            "All selected highlights failed during clip finalization.",
            mock_job_service.fail_job.call_args.kwargs["error"],
        )
        mock_job_service.complete_job.assert_not_called()
        mock_auth_service.refund_credit.assert_called_once_with(user_id=7)

    def test_successful_completion_does_not_refund_credit(self):
        """A completed job (whether all highlights or only some survived
        finalization) must not refund — process_video returning normally
        is the only signal BackgroundJobService looks at."""
        from app.services.background_job_service import BackgroundJobService

        fake_result = {"highlights_found": 2, "all_highlights": []}

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            return_value=fake_result,
        ), patch(
            "app.services.background_job_service.JobService"
        ) as mock_job_service, patch(
            "app.services.background_job_service.SubscriptionService.is_pro_active",
            return_value=False,
        ), patch(
            "app.services.background_job_service.AuthService"
        ) as mock_auth_service, patch(
            "app.services.background_job_service.CleanupService"
        ), patch(
            "app.services.background_job_service.LoggerService"
        ):
            BackgroundJobService.run_pipeline(
                job_id="job-2", video_path="video.mp4", user_id=7
            )

        mock_job_service.complete_job.assert_called_once_with(
            job_id="job-2", result=fake_result
        )
        mock_job_service.fail_job.assert_not_called()
        mock_auth_service.refund_credit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
