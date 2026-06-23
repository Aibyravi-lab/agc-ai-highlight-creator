import time


class StatsService:

    @staticmethod
    def build_stats(
        video_duration: float,
        frames_analyzed: int,
        highlights_found: int,
        processing_time: float
    ):

        return {
            "video_duration": round(
                video_duration,
                2
            ),
            "frames_analyzed": frames_analyzed,
            "highlights_found": highlights_found,
            "processing_time": round(
                processing_time,
                2
            )
        }