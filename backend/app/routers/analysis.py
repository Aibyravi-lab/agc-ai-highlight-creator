from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.services.video_service import get_video_metadata


router = APIRouter(
    prefix="/analysis",
    tags=["Video Analysis"]
)


UPLOAD_FOLDER = "uploads"


@router.get("/{filename}")
def analyze_video(filename: str):
    """
    Analyze uploaded video and return metadata
    """

    file_path = Path(UPLOAD_FOLDER) / filename

    try:
        metadata = get_video_metadata(str(file_path))
        return {
            "status": "success",
            "metadata": metadata
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Video not found"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )