from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path

from app.services.video_service import get_video_metadata
from app.services.logger_service import LoggerService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/analysis",
    tags=["Video Analysis"]
)


UPLOAD_FOLDER = "uploads"


@router.get("/{filename}")
def analyze_video(
    filename: str,
    current_user: dict = Depends(get_current_user)
):

    upload_dir = Path(UPLOAD_FOLDER).resolve()
    file_path = (upload_dir / filename).resolve()

    if not str(file_path).startswith(str(upload_dir)):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

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
        LoggerService.error(
            f"Video analysis failed for {filename}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error."
            }
        )