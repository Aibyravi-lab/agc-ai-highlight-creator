from fastapi import APIRouter, HTTPException

from app.services.pipeline_service import PipelineService
from app.services.progress_service import ProgressService
from app.services.job_service import JobService
from app.services.background_job_service import (
    BackgroundJobService
)


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


@router.post("/start")
def start_video_processing(
    video_path: str
):

    try:

        job_id = (
            JobService.create_job()
        )

        BackgroundJobService.start_job(
            job_id=job_id,
            video_path=video_path
        )

        return {

            "success": True,

            "job_id": job_id,

            "message":
            "Background job started"

        }

    except Exception as error:

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