from fastapi import APIRouter, HTTPException, Depends
from app.services.video_editor_service import VideoEditorService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/editor",
    tags=["Video Editor"]
)


@router.post("/create-clip")
def create_clip(
    video_path: str,
    timestamp: int,
    duration: int = 5,
    current_user: dict = Depends(get_current_user)
):

    try:
        result = VideoEditorService.create_clip(
            video_path,
            timestamp,
            duration
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )