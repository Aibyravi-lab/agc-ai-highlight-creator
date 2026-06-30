from fastapi import APIRouter, HTTPException, Depends

from app.services.pipeline_service import PipelineService
from app.services.progress_service import ProgressService
from app.services.job_service import JobService
from app.services.background_job_service import (
    BackgroundJobService
)
from app.dependencies import get_current_user


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
    video_path: str,
    current_user: dict = Depends(get_current_user)
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


@router.get("/jobs")
def get_all_jobs(
    current_user: dict = Depends(get_current_user)
):

    jobs = JobService.get_all_jobs()

    return {

        "success": True,

        "count":
        len(jobs),

        "data":
        jobs

    }


@router.get("/job/{job_id}")
def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):

    job = JobService.get_job(
        job_id
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {

        "success": True,

        "data": job

    }


@router.get("/jobs/stats")
def get_job_stats(
    current_user: dict = Depends(get_current_user)
):

    return {

        "success": True,

        "data":
        JobService.get_job_stats()

    }


@router.get("/progress")
def get_progress(
    current_user: dict = Depends(get_current_user)
):

    return {
        "success": True,
        "data": ProgressService.get_progress()
    }