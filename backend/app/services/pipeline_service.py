from app.services.frame_service import FrameService
from app.services.vision_service import VisionService
from app.services.highlight_service import HighlightService


class PipelineService:


    @classmethod
    def process_video(cls, video_path: str):

        print("Step 1: Extracting frames...")

        frames_data = FrameService.extract_frames(video_path)


        print("Step 2: Analyzing frames with AI...")


        highlights = []


        for frame in frames_data["frames"]:

            frame_path = (
                f"{frames_data['frame_location']}/"
                f"{frame['frame_name']}"
            )


            vision_result = VisionService.analyze_frame(
                frame_path
            )


            highlight_result = (
                HighlightService.analyze_description(
                    vision_result["description"]
                )
            )


            if highlight_result["is_highlight"]:

                highlights.append({
                    "timestamp": frame["timestamp_second"],

                    "description":
                    vision_result["description"],

                    "score":
                    highlight_result["score"],

                    "keywords":
                    highlight_result["keywords_found"]
                })


        print("Pipeline completed!")


        return {
            "video": video_path,
            "total_frames": len(frames_data["frames"]),
            "highlights_found": len(highlights),
            "highlights": highlights
        }