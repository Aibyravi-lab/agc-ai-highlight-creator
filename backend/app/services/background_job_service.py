from concurrent.futures import ThreadPoolExecutor

from app.config.config import settings
from app.services.job_service import JobService
from app.services.pipeline_service import PipelineService
from app.services.cleanup_service import CleanupService
from app.services.logger_service import LoggerService


class BackgroundJobService:

    _executor = ThreadPoolExecutor(
        max_workers=settings.MAX_CONCURRENT_JOBS,
        thread_name_prefix="pipeline-worker"
    )

    _shutting_down = False

    @classmethod
    def is_accepting_jobs(cls) -> bool:

        return not cls._shutting_down

    @classmethod
    def start_job(
        cls,
        job_id: str,
        video_path: str,
        user_id: int
    ):

        if cls._shutting_down:

            raise RuntimeError(
                "Server is shutting down; not accepting new jobs"
            )

        cls._executor.submit(
            cls.run_pipeline,
            job_id,
            video_path,
            user_id
        )

    @classmethod
    def shutdown(
        cls,
        wait: bool = True
    ):

        cls._shutting_down = True

        LoggerService.info(
            "BackgroundJobService shutting down: "
            "waiting for running jobs to finish"
        )

        cls._executor.shutdown(
            wait=wait
        )

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

        finally:

            CleanupService.cleanup_temp_file(
                video_path
            )

            CleanupService.cleanup()