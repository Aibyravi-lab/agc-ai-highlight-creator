import uuid
from datetime import datetime


class JobService:

    JOBS = {}

    @classmethod
    def create_job(
        cls
    ):

        job_id = str(
            uuid.uuid4()
        )

        cls.JOBS[job_id] = {

            "job_id": job_id,

            "status": "pending",

            "progress": 0,

            "message": "Job Created",

            "result": None,

            "error": None,

            "created_at":
            datetime.utcnow().isoformat(),

            "started_at": None,

            "completed_at": None

        }

        return job_id

    @classmethod
    def get_job(
        cls,
        job_id: str
    ):

        return cls.JOBS.get(
            job_id
        )

    @classmethod
    def get_all_jobs(
        cls
    ):

        return list(
            cls.JOBS.values()
        )

    @classmethod
    def update_job(
        cls,
        job_id: str,
        progress: int,
        message: str,
        status: str = "processing"
    ):

        if job_id not in cls.JOBS:
            return

        if (
            cls.JOBS[job_id]["started_at"]
            is None
        ):
            cls.JOBS[job_id][
                "started_at"
            ] = datetime.utcnow().isoformat()

        cls.JOBS[job_id].update({

            "status": status,

            "progress": progress,

            "message": message

        })

    @classmethod
    def complete_job(
        cls,
        job_id: str,
        result: dict
    ):

        if job_id not in cls.JOBS:
            return

        cls.JOBS[job_id].update({

            "status": "completed",

            "progress": 100,

            "message": "Completed",

            "result": result,

            "completed_at":
            datetime.utcnow().isoformat()

        })

    @classmethod
    def fail_job(
        cls,
        job_id: str,
        error: str
    ):

        if job_id not in cls.JOBS:
            return

        cls.JOBS[job_id].update({

            "status": "failed",

            "message": "Failed",

            "error": error,

            "completed_at":
            datetime.utcnow().isoformat()

        })

    @classmethod
    def get_job_stats(
        cls
    ):

        jobs = cls.JOBS.values()

        return {

            "total_jobs":
            len(cls.JOBS),

            "pending_jobs":
            sum(
                1
                for job in jobs
                if job["status"] == "pending"
            ),

            "processing_jobs":
            sum(
                1
                for job in jobs
                if job["status"] == "processing"
            ),

            "completed_jobs":
            sum(
                1
                for job in jobs
                if job["status"] == "completed"
            ),

            "failed_jobs":
            sum(
                1
                for job in jobs
                if job["status"] == "failed"
            )

        }