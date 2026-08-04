from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict

# VED-OPS-001 / CR-042: response models for the internal Operations API
# (/api/v1/ops/*). Every OpsService section getter fails in isolation and
# degrades to exactly OpsUnavailable's shape — {"status": "unavailable"},
# no other keys — so each section's response_model is a Union of its
# healthy shape and OpsUnavailable, never a single rigid model.
#
# OpsUnavailable forbids extra fields on purpose: it is the disambiguator
# between the two members of every Union below. A healthy payload always
# carries fields OpsUnavailable does not allow, so it can only validate
# against the *Ok model; the degraded {"status": "unavailable"} payload has
# no other fields, so it can only validate against OpsUnavailable. Without
# extra="forbid" here, pydantic's default "ignore extra fields" behavior
# would let a full healthy payload also validate against OpsUnavailable,
# making Union resolution ambiguous.


class OpsUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "unavailable"


class CapabilitiesResponse(BaseModel):
    contract_version: str
    version: str
    features: List[str]


class DiskUsage(BaseModel):
    total_gb: Optional[float]
    used_gb: Optional[float]
    free_gb: Optional[float]
    percent_free: Optional[float]
    status: str


class BuildInfo(BaseModel):
    git_commit: str
    git_tag: str


class FfmpegInfo(BaseModel):
    status: str
    version: str


class HealthChecks(BaseModel):
    uploads: str
    highlights: str
    ffmpeg: str
    disk: str
    database: str


class HealthOk(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    ffmpeg: str
    uptime_seconds: int
    build: BuildInfo
    python_version: str
    ffmpeg_version: str
    disk: DiskUsage
    checks: HealthChecks


HealthResponse = Union[HealthOk, OpsUnavailable]


class SystemOk(BaseModel):
    status: str
    environment: str
    uptime_seconds: Optional[int]
    python_version: str
    ffmpeg: FfmpegInfo
    build: BuildInfo
    disk: DiskUsage


SystemResponse = Union[SystemOk, OpsUnavailable]


class JobsOk(BaseModel):
    status: str
    total_jobs: int
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_time_seconds: Optional[float]


JobsResponse = Union[JobsOk, OpsUnavailable]


class StorageOk(BaseModel):
    status: str
    disk: DiskUsage
    jobs_in_flight: int


StorageResponse = Union[StorageOk, OpsUnavailable]


class UsersOk(BaseModel):
    status: str
    total_users: int
    verified_users: int
    admin_users: int
    internal_users: int


UsersResponse = Union[UsersOk, OpsUnavailable]


class QueueOk(BaseModel):
    status: str
    queue_depth: int
    max_concurrent_jobs: int


QueueResponse = Union[QueueOk, OpsUnavailable]


class SummaryResponse(BaseModel):
    health: HealthResponse
    jobs: JobsResponse
    storage: StorageResponse
    users: UsersResponse
    queue: QueueResponse
