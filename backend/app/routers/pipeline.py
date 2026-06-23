from fastapi import APIRouter, HTTPException
from app.services.pipeline_service import PipelineService
from app.services.progress_service import ProgressService


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

        print("\nDEBUG RESULT:")
        print(result)

        return {
            "success": True,
            "data": result
        }

    except Exception as error:

        print("\nERROR:")
        print(type(error))
        print(error)

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("/progress")
def get_progress():

    return {
        "success": True,
        "data": ProgressService.get_progress()
    }