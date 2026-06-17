from app.services.frame_service import FrameService
from app.services.clip_service import ClipService
from app.services.editor_service import EditorService
from app.services.reel_service import ReelService
from app.services.metadata_service import build_metadata


class PipelineService:

    @classmethod
    def process_video(cls, video_path: str):

        print("Step 1: Extracting frames...")

        frames_data = FrameService.extract_frames(
            video_path
        )

        print("Step 2: Detecting highlights with CLIP AI...")

        highlights = []

        # 15 second cooldown
        last_highlight_time = -15

        for index, frame in enumerate(
            frames_data["frames"]
        ):

            # Analyze every 5th frame
            if index % 5 != 0:
                continue

            print(
                f"Analyzing frame {index + 1}/"
                f"{len(frames_data['frames'])}"
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

            print(
                "CLIP Match:",
                clip_result["best_match"],
                "| Highlight:",
                clip_result["is_highlight"]
            )

            if (
                clip_result["is_highlight"]
                and clip_result["score"] >= 0.80
                and (
                    frame["timestamp_second"]
                    - last_highlight_time >= 15
                )
            ):

                print(
                    "Creating clip at timestamp:",
                    frame["timestamp_second"]
                )

                created_clip = (
                    EditorService.create_clip(
                        video_path=video_path,
                        timestamp=frame["timestamp_second"],
                        duration=5
                    )
                )

                highlights.append({

                    "timestamp":
                    frame["timestamp_second"],

                    "action":
                    clip_result["best_match"],

                    "score":
                    clip_result["score"],

                    "clip_path":
                    created_clip["clip_path"]

                })

                last_highlight_time = (
                    frame["timestamp_second"]
                )

        # Sort by score
        highlights.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # Keep top 10 only
        top_highlights = highlights[:10]

        print("Step 3: Creating final reel...")

        clip_paths = []

        for highlight in top_highlights:

            clip_paths.append(
                highlight["clip_path"]
            )

        final_reel = (
            ReelService.merge_clips(
                clip_paths
            )
        )

        metadata = build_metadata(
            video_path=video_path,
            highlights=top_highlights,
            final_reel_path=final_reel["final_video"]
        )

        print("Pipeline completed!")

        return metadata