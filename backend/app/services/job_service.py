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
            datetime.utcnow().isoformat()

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
    def update_job(
        cls,
        job_id: str,
        progress: int,
        message: str,
        status: str = "processing"
    ):

        if job_id not in cls.JOBS:
            return

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

            "result": result

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

            "error": error

        })