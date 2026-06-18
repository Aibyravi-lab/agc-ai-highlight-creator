from app.services.frame_service import FrameService
from app.services.clip_service import ClipService
from app.services.editor_service import EditorService
from app.services.reel_service import ReelService
from app.services.metadata_service import build_metadata
from app.services.vision_service import VisionService
from app.services.scoring_service import ScoringService
from app.services.duration_service import DurationService
from app.services.thumbnail_rank_service import ThumbnailRankService
from app.services.title_service import TitleService
from app.services.viral_package_service import ViralPackageService
from app.services.whisper_service import WhisperService
from app.services.caption_service import CaptionService


class PipelineService:

    @classmethod
    def process_video(
        cls,
        video_path: str
    ):

        print(
            "Step 1: Extracting frames..."
        )

        frames_data = (
            FrameService.extract_frames(
                video_path
            )
        )

        print(
            "Step 2: Detecting highlights with "
            "CLIP + Motion..."
        )

        highlights = []

        last_highlight_time = -15

        frames = (
            frames_data["frames"]
        )

        for index, frame in enumerate(
            frames
        ):

            if index % 5 != 0:
                continue

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

            if index > 0:

                previous_frame = (
                    f"{frames_data['frame_location']}/"
                    f"{frames[index - 1]['frame_name']}"
                )

                motion_score = (
                    VisionService.calculate_motion_score(
                        previous_frame,
                        frame_path
                    )
                )

            base_score = (

                clip_result["score"] * 0.80

                +

                motion_score * 0.20

            )

            weighted_score = (
                ScoringService.apply_action_weight(
                    score=base_score,
                    action=clip_result[
                        "best_match"
                    ]
                )
            )

            if (

                clip_result[
                    "is_highlight"
                ]

                and

                weighted_score >= 0.50

                and (

                    frame[
                        "timestamp_second"
                    ]

                    -

                    last_highlight_time

                    >= 15

                )

            ):

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

                    "action":
                    clip_result[
                        "best_match"
                    ],

                    "score":
                    final_score,

                    "clip_score":
                    clip_result[
                        "score"
                    ],

                    "motion_score":
                    motion_score,

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
            "Applying smart diversity filter..."
        )

        highlights.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        action_counter = {}

        diversified_highlights = []

        MIN_HIGHLIGHT_GAP = 45

        for highlight in highlights:

            action = (
                highlight["action"]
            )

            if (
                action
                not in action_counter
            ):
                action_counter[
                    action
                ] = 0

            if (
                action_counter[
                    action
                ] >= 1
            ):
                continue

            is_too_close = False

            for selected in (
                diversified_highlights
            ):

                if abs(

                    highlight[
                        "timestamp"
                    ]

                    -

                    selected[
                        "timestamp"
                    ]

                ) < MIN_HIGHLIGHT_GAP:

                    is_too_close = True
                    break

            if is_too_close:
                continue

            action_counter[
                action
            ] += 1

            diversified_highlights.append(
                highlight
            )

        top_highlights = (
            diversified_highlights[:10]
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

        print(
            "Step 3: Creating final reel..."
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

        print(
            "Pipeline completed!"
        )

        return metadata