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
from app.services.logger_service import LoggerService
from app.services.game_profiles.profile_registry import ProfileRegistry
from app.services.game_profiles.base_profile import BaseProfile
from app.services.explainability_service import ExplainabilityService
from app.services.profiler_service import PipelineProfiler


class PipelineService:

    @classmethod
    def process_video(
        cls,
        video_path: str,
        job_id: str | None = None,
        user_id: int | None = None
    ):
        start_time = time.time()
        profiler = PipelineProfiler()

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

        with profiler.track("Frame Extraction"):
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
                profile=profile,
                profiler=profiler
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
        is_silent: bool,
        profiler: PipelineProfiler
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
                    with profiler.track("Motion Detection"):
                        motion_score = MotionScorer.score(
                            previous_path,
                            frame_path
                        )

                audio_score = 0.0
                if not is_silent:
                    with profiler.track("Audio Detection"):
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
        profile: BaseProfile | None,
        profiler: PipelineProfiler,
        clip_text_embedding_cache: dict
    ) -> dict:
        frame_path = (
            f"{frames_location}/"
            f"{frame['frame_name']}"
        )

        with profiler.track("CLIP Detection"):
            clip_result = ClipService.get_highlight_result(
                frame_path,
                profile,
                clip_text_embedding_cache
            )

        motion_score = 0.0
        scene_score = 0.0
        audio_score = 0.0

        if index > 0:
            previous_frame = (
                f"{frames_location}/"
                f"{frames[index - 1]['frame_name']}"
            )
            with profiler.track("Motion Detection"):
                motion_score = MotionScorer.score(
                    previous_frame,
                    frame_path
                )
            with profiler.track("Scene Detection"):
                scene_score = SceneScorer.score(
                    current_frame_path=frame_path,
                    previous_frame_path=previous_frame
                )
            with profiler.track("Audio Detection"):
                audio_score = AudioScorer.score(
                    audio_map=audio_map,
                    timestamp=frame["timestamp_second"]
                )

        with profiler.track("Highlight Scoring"):
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
    def _build_highlight_candidate(
        cls,
        frame: dict,
        scores: dict
    ) -> dict:
        """Lightweight highlight metadata — no FFmpeg work.

        Clip/thumbnail generation is deferred until after merge,
        dedup and ranking so FFmpeg only runs for surviving
        highlights (see _finalize_highlight_clip).
        """
        clip_result = scores["clip_result"]
        weighted_score = scores["weighted_score"]

        clip_duration = DurationService.get_duration(
            clip_result["best_match"]
        )

        return {
            "timestamp": frame["timestamp_second"],
            "category": clip_result["category"],
            "action": clip_result["best_match"],
            "weighted_score": weighted_score,
            "clip_score": scores["clip_score"],
            "motion_score": scores["motion_score"],
            "scene_score": scores["scene_score"],
            "audio_score": scores["audio_score"],
            "duration_score": scores["duration_score"],
            "duration": clip_duration,
            "reason": (
                "CLIP + Motion + "
                "Action Weight + "
                "Thumbnail Rank"
            ),
        }

    @classmethod
    def _finalize_highlight_clip(
        cls,
        video_path: str,
        highlight: dict,
        profiler: PipelineProfiler
    ) -> dict:
        """Runs FFmpeg clip + thumbnail generation for a single
        surviving (post-ranking) highlight and attaches the
        resulting paths/scores onto it, exactly as
        _build_highlight_entry used to do inline during scanning.
        """
        created_clip = EditorService.create_clip(
            video_path=video_path,
            timestamp=highlight["timestamp"],
            duration=highlight["duration"]
        )

        profiler.add(
            "Clip Extraction",
            created_clip.get("clip_creation_seconds", 0.0)
        )

        profiler.add(
            "Thumbnail Generation",
            created_clip.get("thumbnail_generation_seconds", 0.0)
        )

        thumbnail_score = (
            ThumbnailRankService.get_thumbnail_score(
                created_clip["thumbnail_path"]
            )
        )

        final_score = (
            highlight["weighted_score"] * 0.90
            + thumbnail_score * 0.10
        )

        highlight["thumbnail_score"] = thumbnail_score
        highlight["score"] = final_score
        highlight["clip_path"] = created_clip["clip_path"]
        highlight["thumbnail_path"] = created_clip["thumbnail_path"]

        return highlight

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
        profiler: PipelineProfiler,
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

        with profiler.track("Audio Detection"):
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
                    is_silent=is_silent_video,
                    profiler=profiler
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

        # Per-job CLIP text embedding cache (AGC-038.5). Tokenizing,
        # encoding and normalizing the prompt set is identical for
        # every frame in this job; scoped to this call so it never
        # leaks across jobs or users.
        clip_text_embedding_cache: dict = {}

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
                profile=profile,
                profiler=profiler,
                clip_text_embedding_cache=clip_text_embedding_cache
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

                highlight = cls._build_highlight_candidate(
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
                profile=profile,
                profiler=profiler,
                clip_text_embedding_cache=clip_text_embedding_cache
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
                highlight = cls._build_highlight_candidate(
                    frame=frame,
                    scores=scores
                )
                fine_highlights.append(highlight)

        print(
            f"[PASS 2] Complete: "
            f"{len(fine_highlights)} additional highlights"
        )

        # Merge and deduplicate
        with profiler.track("Diversity Filtering"):
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
            with profiler.track("Metadata Generation"):
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
            profiler.print_report()
            return empty_metadata

        for highlight in top_highlights:
            cls._finalize_highlight_clip(
                video_path=video_path,
                highlight=highlight,
                profiler=profiler
            )

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
        profiler.add(
            "Reel Generation",
            final_reel.get("reel_generation_seconds", 0.0)
        )
        profiler.add(
            "Vertical Reel Generation",
            final_reel.get("vertical_reel_seconds", 0.0)
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
                ],
                profiler=profiler
            )
        )

        with profiler.track("Whisper Post Processing"):
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
                caption_text=caption_text,
                profiler=profiler
            )
        )

        with profiler.track("Metadata Generation"):
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
        LoggerService.info(
            "Whisper transcription complete: "
            f"language={transcription.get('language')}, "
            f"segments={len(transcription.get('segments', []))}, "
            f"text_length={len(transcription.get('text', ''))}"
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

        LoggerService.info(
            f"Caption text applied: length={len(caption_text)}"
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

        with profiler.track("Result Export"):
            result_json = (
                ResultExportService.save_result(
                    metadata
                )
            )

        metadata[
            "result_json"
        ] = result_json

        if user_id is not None:
            try:
                with profiler.track("History Registration"):
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

                with profiler.track("Project Registration"):
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

            except Exception as registration_error:

                LoggerService.error(
                    f"Artifact registration failed: "
                    f"{registration_error}",
                    user_id=user_id,
                    job_id=job_id
                )

                metadata[
                    "history_saved"
                ] = False
        else:
            metadata[
                "history_saved"
            ] = False
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

        profiler.print_report()

        return metadata
