from fastapi import APIRouter, HTTPException, Depends
from app.services.frame_service import FrameService
from app.services.logger_service import LoggerService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/frames",
    tags=["Frame Extraction"]
)


@router.post("/extract")
def extract_frames(
    video_path: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        result = FrameService.extract_frames(video_path)

        return {
            "success": True,
            "message": "Frames extracted successfully",
            "data": result
        }

    except Exception as error:
        LoggerService.error(
            f"Frame extraction failed: {error}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error."
            }
        )