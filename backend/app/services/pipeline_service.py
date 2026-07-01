import time
from pathlib import Path
from app.services.stats_service import StatsService
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


class PipelineService:

    @classmethod
    def process_video(
        cls,
        video_path: str,
        job_id: str | None = None,
        user_id: int | None = None
    ):
        start_time = time.time()
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

        highlights = []

        audio_data = (
            AudioService.build_audio_map(
                video_path=video_path
            )
        )

        audio_map = (
            audio_data["audio_map"]
        )

        is_silent_video = (
            audio_data["is_silent"]
        )

        last_highlight_time = -15

        frames = (
            frames_data["frames"]
        )
        frames_analyzed = 0

        for index, frame in enumerate(
            frames
        ):

            if index % 5 != 0:
                continue
            frames_analyzed += 1
            print(
                f"Analyzing frame "
                f"{index + 1}/"
                f"{len(frames)}"
            )

            frame_path = (
                f"{frames_data['frame_location']}/"
                f"{frame['frame_name']}"
            )

            clip_result = (
                ClipService.get_highlight_result(
                    frame_path
                )
            )

            motion_score = 0.0
            scene_score = 0.0
            audio_score = 0.0

            if index > 0:

                previous_frame = (
                    f"{frames_data['frame_location']}/"
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

            duration_score = DurationScorer.score(
                clip_result["best_match"]
            )

            weighted_score = ScoringOrchestrator.compute_weighted_score(
                clip_score=clip_score,
                motion_score=motion_score,
                audio_score=audio_score,
                scene_score=scene_score,
                duration_score=duration_score,
                action=clip_result["best_match"],
                is_silent=is_silent_video
            )
            print(
                "DEBUG:",
                frame["timestamp_second"],
                clip_result["best_match"],
                "clip=", round(clip_score, 3),
                "motion=", round(motion_score, 3),
                "scene=", round(scene_score, 3),
                "audio=", round(audio_score, 3),
                "final=", round(weighted_score, 3)
            )
            if (

                clip_result[
                    "is_highlight"
                ]

                and

                weighted_score >= 0.20

                and (

                    frame[
                        "timestamp_second"
                    ]

                    -

                    last_highlight_time

                    >= 15

                )

            ):
                print(
                    "HIGHLIGHT FOUND:",
                    frame["timestamp_second"],
                    weighted_score
                )

                clip_duration = (
                    DurationService.get_duration(
                        clip_result[
                            "best_match"
                        ]
                    )
                )

                created_clip = (
                    EditorService.create_clip(
                        video_path=video_path,
                        timestamp=frame[
                            "timestamp_second"
                        ],
                        duration=clip_duration
                    )
                )

                thumbnail_score = (
                    ThumbnailRankService.get_thumbnail_score(
                        created_clip[
                            "thumbnail_path"
                        ]
                    )
                )

                final_score = (

                    weighted_score * 0.90

                    +

                    thumbnail_score * 0.10

                )

                highlights.append({

                    "timestamp":
                    frame[
                        "timestamp_second"
                    ],
                    "category":
                    clip_result["category"],

                    "action":
                    clip_result[
                        "best_match"
                    ],

                    "score":
                    final_score,

                    "weighted_score":
                    weighted_score,

                    "clip_score":
                    clip_score,

                    "motion_score":
                    motion_score,

                    "scene_score":
                    scene_score,

                    "audio_score":
                    audio_score,

                    "duration_score":
                    duration_score,

                    "thumbnail_score":
                    thumbnail_score,

                    "duration":
                    clip_duration,

                    "reason":
                    (
                        "CLIP + Motion + "
                        "Action Weight + "
                        "Thumbnail Rank"
                    ),

                    "clip_path":
                    created_clip[
                        "clip_path"
                    ],

                    "thumbnail_path":
                    created_clip[
                        "thumbnail_path"
                    ]

                })

                last_highlight_time = (
                    frame[
                        "timestamp_second"
                    ]
                )

        print(
            "Applying highlight ranking..."
        )

        top_highlights = (
            HighlightRankingService.rank(
                highlights
            )
        )

        if len(top_highlights) == 0:

            return build_metadata(
                video_path=video_path,
                highlights=[],
                final_reel_path="",
                vertical_reel_path="",
                reel_title="",
                reel_description="",
                reel_hashtags=[]
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
