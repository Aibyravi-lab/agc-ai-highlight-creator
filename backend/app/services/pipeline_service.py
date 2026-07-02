import time
import numpy as np
from pathlib import Path
from app.config.config import settings
from app.services.stats_service import StatsService
from app.services.cleanup_service import CleanupService
from app.services.result_export_service import ResultExportService
from app.services.history_service import HistoryService
from app.services.frame_service import FrameService
from app.services.clip_service import ClipService
from app.services.editor_service import EditorService
from app.services.reel_service import ReelService
from app.services.metadata_service import build_metadata
from app.services.duration_service import DurationService
from app.services.scoring import (
    ClipScorer,
    MotionScorer,
    AudioScorer,
    SceneScorer,
    DurationScorer,
    ScoringOrchestrator,
)
from app.services.thumbnail_rank_service import ThumbnailRankService
from app.services.title_service import TitleService
from app.services.viral_package_service import ViralPackageService
from app.services.whisper_service import WhisperService
from app.services.caption_service import CaptionService
from app.services.audio_service import AudioService
from app.services.progress_service import ProgressService
from app.services.job_service import JobService
from app.services.highlight_ranking_service import HighlightRankingService
from app.services.project_service import ProjectService
from app.services.game_profiles.profile_registry import ProfileRegistry
from app.services.game_profiles.base_profile import BaseProfile
from app.services.explainability_service import ExplainabilityService


class PipelineService:

    @classmethod
    def process_video(
        cls,
        video_path: str,
        job_id: str | None = None,
        user_id: int | None = None
    ):
        start_time = time.time()

        profile = ProfileRegistry.detect_profile(video_path)
        print(
            f"Game profile detected: "
            f"{profile.game_name}"
        )

        ProgressService.update(
            progress=5,
            status="Starting Pipeline"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=5,
                message="Starting Pipeline"
            )
        ProgressService.update(
            progress=10,
            status="Extracting Frames"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=10,
                message="Extracting Frames"
            )
        print(
            "Step 1: Extracting frames..."
        )

        frames_data = (
            FrameService.extract_frames(
                video_path
            )
        )

        frames_folder = (
            frames_data["frame_location"]
        )

        try:

            return cls._run_pipeline(
                video_path=video_path,
                job_id=job_id,
                user_id=user_id,
                frames_data=frames_data,
                start_time=start_time,
                profile=profile
            )

        finally:

            CleanupService.cleanup_temp_folder(
                frames_folder
            )

    @classmethod
    def _compute_adaptive_threshold(
        cls,
        frames: list,
        frames_location: str,
        audio_map: dict,
        is_silent: bool
    ) -> float:
        try:
            energy_scores: list[float] = []

            for index, frame in enumerate(frames):

                if index % 5 != 0:
                    continue

                frame_path = (
                    f"{frames_location}/"
                    f"{frame['frame_name']}"
                )

                motion_score = 0.0
                if index > 0:
                    previous_path = (
                        f"{frames_location}/"
                        f"{frames[index - 1]['frame_name']}"
                    )
                    motion_score = MotionScorer.score(
                        previous_path,
                        frame_path
                    )

                audio_score = 0.0
                if not is_silent:
                    audio_score = AudioScorer.score(
                        audio_map=audio_map,
                        timestamp=frame["timestamp_second"]
                    )

                energy = (
                    motion_score * 0.60
                    + audio_score * 0.40
                )
                energy_scores.append(energy)

            if not energy_scores:
                print(
                    "[ADAPTIVE THRESHOLD] No energy scores — "
                    f"using default: "
                    f"{settings.DEFAULT_HIGHLIGHT_THRESHOLD}"
                )
                return settings.DEFAULT_HIGHLIGHT_THRESHOLD

            threshold = float(max(
                settings.MIN_ADAPTIVE_THRESHOLD,
                np.percentile(
                    energy_scores,
                    settings.ADAPTIVE_THRESHOLD_PERCENTILE
                )
            ))
            print(
                f"[ADAPTIVE THRESHOLD] threshold={round(threshold, 4)} "
                f"(percentile={settings.ADAPTIVE_THRESHOLD_PERCENTILE}, "
                f"samples={len(energy_scores)}, "
                f"min={round(min(energy_scores), 4)}, "
                f"max={round(max(energy_scores), 4)})"
            )
            return threshold

        except Exception as ex:
            print(
                f"[ADAPTIVE THRESHOLD] Computation failed: {ex} — "
                f"using default: "
                f"{settings.DEFAULT_HIGHLIGHT_THRESHOLD}"
            )
            return settings.DEFAULT_HIGHLIGHT_THRESHOLD

    @classmethod
    def _score_single_frame(
        cls,
        frames: list,
        frames_location: str,
        index: int,
        frame: dict,
        audio_map: dict,
        is_silent: bool,
        profile: BaseProfile | None
    ) -> dict:
        frame_path = (
            f"{frames_location}/"
            f"{frame['frame_name']}"
        )

        clip_result = ClipService.get_highlight_result(
            frame_path,
            profile
        )

        motion_score = 0.0
        scene_score = 0.0
        audio_score = 0.0

        if index > 0:
            previous_frame = (
                f"{frames_location}/"
                f"{frames[index - 1]['frame_name']}"
            )
            motion_score = MotionScorer.score(
                previous_frame,
                frame_path
            )
            scene_score = SceneScorer.score(
                current_frame_path=frame_path,
                previous_frame_path=previous_frame
            )
            audio_score = AudioScorer.score(
                audio_map=audio_map,
                timestamp=frame["timestamp_second"]
            )

        clip_score = ClipScorer.score(clip_result)
        duration_score = DurationScorer.score(clip_result["best_match"])

        weighted_score = ScoringOrchestrator.compute_weighted_score(
            clip_score=clip_score,
            motion_score=motion_score,
            audio_score=audio_score,
            scene_score=scene_score,
            duration_score=duration_score,
            action=clip_result["best_match"],
            is_silent=is_silent,
            weights=profile.scoring_weights if profile is not None else None,
            category_overrides=profile.category_weight_overrides if profile is not None else None
        )

        return {
            "clip_result": clip_result,
            "clip_score": clip_score,
            "motion_score": motion_score,
            "scene_score": scene_score,
            "audio_score": audio_score,
            "duration_score": duration_score,
            "weighted_score": weighted_score,
        }

    @classmethod
    def _build_highlight_entry(
        cls,
        video_path: str,
        frame: dict,
        scores: dict
    ) -> dict:
        clip_result = scores["clip_result"]
        weighted_score = scores["weighted_score"]

        clip_duration = DurationService.get_duration(
            clip_result["best_match"]
        )

        created_clip = EditorService.create_clip(
            video_path=video_path,
            timestamp=frame["timestamp_second"],
            duration=clip_duration
        )

        thumbnail_score = (
            ThumbnailRankService.get_thumbnail_score(
                created_clip["thumbnail_path"]
            )
        )

        final_score = (
            weighted_score * 0.90
            + thumbnail_score * 0.10
        )

        return {
            "timestamp": frame["timestamp_second"],
            "category": clip_result["category"],
            "action": clip_result["best_match"],
            "score": final_score,
            "weighted_score": weighted_score,
            "clip_score": scores["clip_score"],
            "motion_score": scores["motion_score"],
            "scene_score": scores["scene_score"],
            "audio_score": scores["audio_score"],
            "duration_score": scores["duration_score"],
            "thumbnail_score": thumbnail_score,
            "duration": clip_duration,
            "reason": (
                "CLIP + Motion + "
                "Action Weight + "
                "Thumbnail Rank"
            ),
            "clip_path": created_clip["clip_path"],
            "thumbnail_path": created_clip["thumbnail_path"],
        }

    @classmethod
    def _merge_and_deduplicate(cls, highlights: list) -> list:
        """Keep highest-scoring highlight when two are within 15 seconds."""
        sorted_highlights = sorted(
            highlights,
            key=lambda h: h["weighted_score"],
            reverse=True
        )
        merged: list = []
        for h in sorted_highlights:
            if all(
                abs(h["timestamp"] - kept["timestamp"]) > 15
                for kept in merged
            ):
                merged.append(h)
        return merged

    @classmethod
    def _run_pipeline(
        cls,
        video_path: str,
        job_id: str | None,
        user_id: int | None,
        frames_data: dict,
        start_time: float,
        profile: BaseProfile | None = None
    ):

        ProgressService.update(
            progress=35,
            status="Detecting Highlights"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=35,
                message="Detecting Highlights"
            )
        print(
            "Step 2: Detecting highlights with "
            "CLIP + Motion..."
        )

        audio_data = (
            AudioService.build_audio_map(
                video_path=video_path
            )
        )

        audio_map = audio_data["audio_map"]
        is_silent_video = audio_data["is_silent"]

        if settings.ADAPTIVE_THRESHOLD_ENABLED:
            print(
                "[ADAPTIVE THRESHOLD] Running pre-scan..."
            )
            adaptive_threshold = (
                cls._compute_adaptive_threshold(
                    frames=frames_data["frames"],
                    frames_location=frames_data["frame_location"],
                    audio_map=audio_map,
                    is_silent=is_silent_video
                )
            )
        else:
            adaptive_threshold = (
                settings.DEFAULT_HIGHLIGHT_THRESHOLD
            )
            print(
                "[ADAPTIVE THRESHOLD] Disabled — "
                f"using default: {adaptive_threshold}"
            )

        frames = frames_data["frames"]
        frames_location = frames_data["frame_location"]
        frames_analyzed = 0

        # Pass 1 — Coarse Scan: every 5th frame
        print("[PASS 1] Coarse scan starting...")
        coarse_trigger = (
            adaptive_threshold
            * settings.COARSE_TRIGGER_MULTIPLIER
        )
        coarse_highlights: list = []
        candidate_windows: list[tuple[float, float]] = []
        coarse_frame_indices: set[int] = set()
        last_highlight_time: float = -15.0

        for index, frame in enumerate(frames):

            if index % 5 != 0:
                continue

            coarse_frame_indices.add(index)
            frames_analyzed += 1
            print(
                f"Analyzing frame "
                f"{index + 1}/"
                f"{len(frames)}"
            )

            scores = cls._score_single_frame(
                frames=frames,
                frames_location=frames_location,
                index=index,
                frame=frame,
                audio_map=audio_map,
                is_silent=is_silent_video,
                profile=profile
            )

            clip_result = scores["clip_result"]
            weighted_score = scores["weighted_score"]

            print(
                "DEBUG:",
                frame["timestamp_second"],
                clip_result["best_match"],
                "clip=", round(scores["clip_score"], 3),
                "motion=", round(scores["motion_score"], 3),
                "scene=", round(scores["scene_score"], 3),
                "audio=", round(scores["audio_score"], 3),
                "final=", round(weighted_score, 3)
            )

            if weighted_score >= coarse_trigger:
                ts = float(frame["timestamp_second"])
                candidate_windows.append((
                    ts - settings.FINE_SCAN_WINDOW_SECONDS,
                    ts + settings.FINE_SCAN_WINDOW_SECONDS
                ))

            if (
                clip_result["is_highlight"]
                and weighted_score >= adaptive_threshold
                and (
                    frame["timestamp_second"]
                    - last_highlight_time
                    >= 15
                )
            ):
                print(
                    "HIGHLIGHT FOUND:",
                    frame["timestamp_second"],
                    weighted_score
                )

                highlight = cls._build_highlight_entry(
                    video_path=video_path,
                    frame=frame,
                    scores=scores
                )
                coarse_highlights.append(highlight)
                last_highlight_time = float(
                    frame["timestamp_second"]
                )

        print(
            f"[PASS 1] Complete: "
            f"{len(coarse_highlights)} highlights, "
            f"{len(candidate_windows)} candidate windows"
        )

        # Pass 2 — Fine Scan: every frame in candidate windows
        ProgressService.update(
            progress=55,
            status="Fine Scan"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=55,
                message="Fine Scan"
            )
        print("[PASS 2] Fine scan starting...")

        fine_scan_indices: set[int] = set()
        for start_ts, end_ts in candidate_windows:
            for i, frame in enumerate(frames):
                if (
                    i not in coarse_frame_indices
                    and start_ts <= frame["timestamp_second"] <= end_ts
                ):
                    fine_scan_indices.add(i)

        fine_highlights: list = []

        for index in sorted(fine_scan_indices):
            frame = frames[index]
            frames_analyzed += 1
            print(
                f"[PASS 2] Frame "
                f"{index + 1}/{len(frames)} "
                f"@ {frame['timestamp_second']}s"
            )

            scores = cls._score_single_frame(
                frames=frames,
                frames_location=frames_location,
                index=index,
                frame=frame,
                audio_map=audio_map,
                is_silent=is_silent_video,
                profile=profile
            )

            clip_result = scores["clip_result"]
            weighted_score = scores["weighted_score"]

            print(
                "DEBUG [FINE]:",
                frame["timestamp_second"],
                clip_result["best_match"],
                "clip=", round(scores["clip_score"], 3),
                "motion=", round(scores["motion_score"], 3),
                "scene=", round(scores["scene_score"], 3),
                "audio=", round(scores["audio_score"], 3),
                "final=", round(weighted_score, 3)
            )

            if (
                clip_result["is_highlight"]
                and weighted_score >= adaptive_threshold
            ):
                print(
                    "FINE HIGHLIGHT FOUND:",
                    frame["timestamp_second"],
                    weighted_score
                )
                highlight = cls._build_highlight_entry(
                    video_path=video_path,
                    frame=frame,
                    scores=scores
                )
                fine_highlights.append(highlight)

        print(
            f"[PASS 2] Complete: "
            f"{len(fine_highlights)} additional highlights"
        )

        # Merge and deduplicate
        all_highlights = coarse_highlights + fine_highlights
        highlights = cls._merge_and_deduplicate(all_highlights)
        duplicates_removed = len(all_highlights) - len(highlights)
        print(
            f"[MERGE] Total before dedup: {len(all_highlights)}, "
            f"After dedup: {len(highlights)}, "
            f"Duplicates removed: {duplicates_removed}"
        )

        print(
            "Applying highlight ranking..."
        )

        top_highlights = (
            HighlightRankingService.rank(
                highlights,
                profile=profile
            )
        )

        profile_name = profile.game_name if profile is not None else "Default"
        category_overrides = (
            profile.category_weight_overrides if profile is not None else None
        )
        ranking_bonus = (
            profile.ranking_bonus if profile is not None else {}
        )
        for h in top_highlights:
            h["explanation"] = ExplainabilityService.build(
                clip_score=h["clip_score"],
                motion_score=h["motion_score"],
                scene_score=h["scene_score"],
                audio_score=h["audio_score"],
                duration_score=h["duration_score"],
                weighted_score=h["weighted_score"],
                ranking_score=h.get("ranking_score", 0.0),
                adaptive_threshold=adaptive_threshold,
                profile_name=profile_name,
                action=h["action"],
                category=h.get("category", ""),
                category_overrides=category_overrides,
                profile_ranking_bonus=ranking_bonus,
            )

        if len(top_highlights) == 0:
            empty_metadata = build_metadata(
                video_path=video_path,
                highlights=[],
                final_reel_path="",
                vertical_reel_path="",
                reel_title="",
                reel_description="",
                reel_hashtags=[]
            )
            empty_metadata["adaptive_threshold"] = round(adaptive_threshold, 4)
            return empty_metadata
        ProgressService.update(
            progress=70,
            status="Generating Reel"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=70,
                message="Generating Reel"
            )
        print(
            "Step 3: Creating final reel..."
        )
        print("\nTOP HIGHLIGHTS:")

        for item in top_highlights:

            print(
                item["timestamp"],
                item["category"],
                item["action"],
                round(item["score"], 3)
             )
        clip_paths = []

        for highlight in (
            top_highlights
        ):

            clip_paths.append(
                highlight[
                    "clip_path"
                ]
            )

        final_reel = (
            ReelService.merge_clips(
                clip_paths
            )
        )

        reel_title = (
            TitleService.generate_title(
                top_highlights
            )
        )

        viral_package = (
            ViralPackageService.generate_package(
                top_highlights
            )
        )
        ProgressService.update(
            progress=85,
            status="Transcribing Audio"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=85,
                message="Transcribing Audio"
            )
        print(
            "Step 4: Transcribing audio..."
        )

        transcription = (
            WhisperService.transcribe_video(
                final_reel[
                    "final_video"
                ]
            )
        )

        caption_text = (
            transcription[
                "text"
            ][:100]
        )
        ProgressService.update(
            progress=95,
            status="Adding Captions"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=95,
                message="Adding Captions"
            )
        print(
            "Step 5: Adding captions..."
        )

        captioned_reel = (
            CaptionService.add_captions(
                video_path=final_reel[
                    "final_video"
                ],
                caption_text=caption_text
            )
        )

        metadata = build_metadata(
            video_path=video_path,
            highlights=top_highlights,
            final_reel_path=final_reel[
                "final_video"
            ],
            vertical_reel_path=final_reel[
                "vertical_video"
            ],
            reel_title=reel_title,
            reel_description=viral_package[
                "description"
            ],
            reel_hashtags=viral_package[
                "hashtags"
            ]
        )
        print(
            "WHISPER RESULT:",
            transcription
        )

        metadata[
            "captioned_reel"
        ] = captioned_reel

        metadata[
            "transcription"
        ] = caption_text

        metadata[
            "adaptive_threshold"
        ] = round(adaptive_threshold, 4)

        print(
            "Generated Title:",
            reel_title
        )

        print(
            "Generated Description:",
            viral_package[
                "description"
            ]
        )

        print(
            "Generated Hashtags:",
            ", ".join(
                viral_package[
                    "hashtags"
                ]
            )
        )

        print(
            "Captioned Reel:",
            captioned_reel
        )

        print(
            "Transcription:",
            caption_text
        )

        processing_time = (
            time.time() - start_time
        )

        stats = (
            StatsService.build_stats(
                video_duration=
                frames_data["duration"],

                frames_analyzed=
                frames_analyzed,

                highlights_found=
                len(top_highlights),

                processing_time=
                processing_time
            )
        )

        metadata[
            "stats"
        ] = stats

        result_json = (
            ResultExportService.save_result(
                metadata
            )
        )

        metadata[
            "result_json"
        ] = result_json

        if user_id is not None:
            HistoryService.add_history(
                video_name=
                Path(video_path).name,

                reel_path=
                final_reel[
                    "final_video"
                ],

                highlights_count=
                len(top_highlights),

                user_id=user_id
            )

            ProjectService.create_project(
                user_id=user_id,
                job_id=job_id,
                original_video_name=
                Path(video_path).name,

                thumbnail_path=
                metadata.get("thumbnail"),

                horizontal_reel_path=
                metadata.get("final_reel"),

                vertical_reel_path=
                metadata.get(
                    "vertical_reel"
                ) or None,

                metadata_json_path=
                metadata.get(
                    "result_json"
                ) or None,
            )

        metadata[
            "history_saved"
        ] = True
        ProgressService.update(
            progress=100,
            status="Completed"
        )
        if job_id is not None:
            JobService.update_job(
                job_id=job_id,
                progress=100,
                message="Completed"
            )
        print(
            "Pipeline completed!"
        )


        return metadata
