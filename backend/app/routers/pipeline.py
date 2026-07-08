from fastapi import APIRouter, HTTPException, Depends

from app.services.job_service import JobService
from app.services.auth_service import AuthService
from app.services.subscription_service import SubscriptionService
from app.services.background_job_service import (
    BackgroundJobService
)
from app.config.config import settings
from app.services.logger_service import LoggerService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/pipeline",
    tags=["AI Pipeline"]
)


class PipelineError:
    MAX_CONCURRENT_JOBS = "MAX_CONCURRENT_JOBS"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    ENDPOINT_REMOVED = "ENDPOINT_REMOVED"


def _sanitize_job(job: dict) -> dict:

    if job.get("status") != "failed":
        return job

    sanitized = dict(job)

    sanitized["error"] = {
        "code": "INTERNAL_ERROR",
        "message": "Unexpected server error."
    }

    return sanitized


def _insufficient_credits_error() -> HTTPException:

    return HTTPException(
        status_code=403,
        detail={
            "code": PipelineError.INSUFFICIENT_CREDITS,
            "message": (
                "You have no free credits remaining. "
                "Upgrade your plan to continue generating highlights."
            )
        }
    )


@router.post("/process")
def process_video(
    video_path: str,
    current_user: dict = Depends(get_current_user)
):

    # AGC-062.3: retired — this route ran the AI pipeline synchronously
    # with no subscription/credit enforcement, unlike /pipeline/start.
    # Kept registered (rather than deleted) so callers get an explicit
    # 410 instead of a generic 404.
    raise HTTPException(
        status_code=410,
        detail={
            "code": PipelineError.ENDPOINT_REMOVED,
            "message": (
                "This endpoint has been retired. "
                "Use POST /pipeline/start."
            )
        }
    )


@router.post("/start")
def start_video_processing(
    video_path: str,
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    if not BackgroundJobService.is_accepting_jobs():

        raise HTTPException(
            status_code=503,
            detail={
                "code": PipelineError.SERVICE_UNAVAILABLE,
                "message": (
                    "Server is shutting down. "
                    "Please try again shortly."
                )
            }
        )

    running = (
        JobService.get_running_job_count(
            user_id=user_id
        )
    )

    if running >= settings.MAX_CONCURRENT_JOBS_PER_USER:

        raise HTTPException(
            status_code=429,
            detail={
                "code": PipelineError.MAX_CONCURRENT_JOBS,
                "message": (
                    "Maximum concurrent jobs reached. "
                    "Please wait for an existing job to finish."
                )
            }
        )

    if not SubscriptionService.is_pro_active(user_id):

        if current_user.get("credits_remaining", 0) <= 0:

            raise _insufficient_credits_error()

        if not AuthService.deduct_credit(user_id):

            raise _insufficient_credits_error()

    try:

        job_id = (
            JobService.create_job(
                user_id=user_id
            )
        )

        BackgroundJobService.start_job(
            job_id=job_id,
            video_path=video_path,
            user_id=user_id
        )

        return {

            "success": True,

            "job_id": job_id,

            "message":
            "Background job started"

        }

    except Exception as error:

        AuthService.refund_credit(user_id)

        LoggerService.error(
            f"Pipeline job start failed for user {user_id}: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error."
            }
        )


@router.get("/jobs")
def get_all_jobs(
    current_user: dict = Depends(get_current_user)
):

    jobs = JobService.get_all_jobs(
        user_id=current_user["id"]
    )

    sanitized_jobs = [
        _sanitize_job(job)
        for job in jobs
    ]

    return {

        "success": True,

        "count":
        len(sanitized_jobs),

        "data":
        sanitized_jobs

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

    if job.get("user_id") != current_user["id"]:

        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    return {

        "success": True,

        "data": _sanitize_job(job)

    }


@router.get("/jobs/stats")
def get_job_stats(
    current_user: dict = Depends(get_current_user)
):

    return {

        "success": True,

        "data":
        JobService.get_job_stats(
            user_id=current_user["id"]
        )

    }


@router.get("/progress")
def get_progress(
    current_user: dict = Depends(get_current_user)
):

    return {
        "success": True,
        "data": JobService.get_user_active_progress(
            user_id=current_user["id"]
        )
    }