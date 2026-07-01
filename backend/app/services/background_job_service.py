import threading

from app.services.job_service import JobService
from app.services.pipeline_service import PipelineService
from app.services.cleanup_service import CleanupService
from app.services.logger_service import LoggerService


class BackgroundJobService:

    @classmethod
    def start_job(
        cls,
        job_id: str,
        video_path: str,
        user_id: int
    ):

        worker = threading.Thread(
            target=cls.run_pipeline,
            args=(
                job_id,
                video_path,
                user_id
            ),
            daemon=True
        )

        worker.start()

    @classmethod
    def run_pipeline(
        cls,
        job_id: str,
        video_path: str,
        user_id: int
    ):

        try:

            LoggerService.info(
                f"Job Started: {job_id}"
            )

            JobService.update_job(
                job_id=job_id,
                progress=1,
                message="Pipeline Started"
            )

            result = PipelineService.process_video(
                job_id=job_id,
                video_path=video_path,
                user_id=user_id
            )

            JobService.complete_job(
                job_id=job_id,
                result=result
            )

            CleanupService.cleanup()

            LoggerService.info(
                f"Job Completed: {job_id}"
            )

        except Exception as error:

            LoggerService.error(
                f"Job Failed: {job_id} | {error}"
            )

            JobService.fail_job(
                job_id=job_id,
                error=str(error)
            )