import threading

from app.services.job_service import JobService
from app.services.pipeline_service import PipelineService


class BackgroundJobService:

    @classmethod
    def start_job(
        cls,
        job_id: str,
        video_path: str
    ):

        worker = threading.Thread(
            target=cls.run_pipeline,
            args=(
                job_id,
                video_path
            ),
            daemon=True
        )

        worker.start()

    @classmethod
    def run_pipeline(
        cls,
        job_id: str,
        video_path: str
    ):

        try:

            JobService.update_job(
                job_id=job_id,
                progress=1,
                message="Pipeline Started"
            )

            result = (
                PipelineService.process_video(
                    video_path
                )
            )

            JobService.complete_job(
                job_id=job_id,
                result=result
            )

        except Exception as error:

            JobService.fail_job(
                job_id=job_id,
                error=str(error)
            )