from typing import List, Dict


def build_metadata(
    video_path: str,
    highlights: List[Dict],
    final_reel_path: str
):

    best_highlight = None

    if highlights:

        best_highlight = max(
            highlights,
            key=lambda x: x["score"]
        )

    return {

        "video": video_path,

        "highlights_found": len(highlights),

        "best_highlight": best_highlight,

        "all_highlights": highlights,

        "final_reel": final_reel_path

    }