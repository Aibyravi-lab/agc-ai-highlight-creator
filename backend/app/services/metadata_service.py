from typing import List, Dict

from app.services.social_export_service import (
    SocialExportService
)


def build_metadata(
    video_path: str,
    highlights: List[Dict],
    final_reel_path: str,
    vertical_reel_path: str = "",
    reel_title: str = "",
    reel_description: str = "",
    reel_hashtags: list = None
):

    best_highlight = None

    thumbnail_path = None

    if reel_hashtags is None:
        reel_hashtags = []

    if highlights:

        best_highlight = max(
            highlights,
            key=lambda x: x["score"]
        )

        thumbnail_path = (
            best_highlight[
                "thumbnail_path"
            ]
        )

    social_exports = (
        SocialExportService.build_exports(
            title=reel_title,
            description=reel_description,
            hashtags=reel_hashtags
        )
    )

    return {

        "video":
        video_path,

        "title":
        reel_title,

        "description":
        reel_description,

        "hashtags":
        reel_hashtags,

        "social_exports":
        social_exports,

        "highlights_found":
        len(highlights),

        "best_highlight":
        best_highlight,

        "all_highlights":
        highlights,

        "final_reel":
        final_reel_path,

        "vertical_reel":
        vertical_reel_path,

        "thumbnail":
        thumbnail_path

    }