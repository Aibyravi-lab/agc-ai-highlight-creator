from fastapi import APIRouter, HTTPException
from app.services.pipeline_service import PipelineService


router = APIRouter(
    prefix="/pipeline",
    tags=["AI Pipeline"]
)


@router.post("/process")
def process_video(video_path: str):

    try:
        result = PipelineService.process_video(
            video_path
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