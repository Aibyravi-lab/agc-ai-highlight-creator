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