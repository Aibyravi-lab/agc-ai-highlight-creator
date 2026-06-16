from fastapi import APIRouter, HTTPException
from app.services.frame_service import FrameService


router = APIRouter(
    prefix="/frames",
    tags=["Frame Extraction"]
)


@router.post("/extract")
def extract_frames(video_path: str):
    try:
        result = FrameService.extract_frames(video_path)

        return {
            "success": True,
            "message": "Frames extracted successfully",
            "data": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )