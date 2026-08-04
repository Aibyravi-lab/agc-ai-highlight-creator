from fastapi import APIRouter, Depends

from app.dependencies import verify_ops_api_key
from app.schemas.ops import (
    CapabilitiesResponse,
    HealthResponse,
    JobsResponse,
    QueueResponse,
    StorageResponse,
    SummaryResponse,
    SystemResponse,
    UsersResponse,
)
from app.services.ops_service import OpsService

# VED-OPS-001: internal Operations API — read-only, aggregate-only, never
# exposed for customer use. Auth is a dedicated ops API key
# (verify_ops_api_key), fully independent of customer JWT auth.
router = APIRouter(
    prefix="/api/v1/ops",
    tags=["Operations"],
)


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities(_: None = Depends(verify_ops_api_key)) -> CapabilitiesResponse:

    return OpsService.get_capabilities()


@router.get("/health", response_model=HealthResponse)
def health(_: None = Depends(verify_ops_api_key)) -> HealthResponse:

    return OpsService.get_health()


@router.get("/system", response_model=SystemResponse)
def system(_: None = Depends(verify_ops_api_key)) -> SystemResponse:

    return OpsService.get_system()


@router.get("/jobs", response_model=JobsResponse)
def jobs(_: None = Depends(verify_ops_api_key)) -> JobsResponse:

    return OpsService.get_jobs()


@router.get("/storage", response_model=StorageResponse)
def storage(_: None = Depends(verify_ops_api_key)) -> StorageResponse:

    return OpsService.get_storage()


@router.get("/users", response_model=UsersResponse)
def users(_: None = Depends(verify_ops_api_key)) -> UsersResponse:

    return OpsService.get_users()


@router.get("/queue", response_model=QueueResponse)
def queue(_: None = Depends(verify_ops_api_key)) -> QueueResponse:

    return OpsService.get_queue()


@router.get("/summary", response_model=SummaryResponse)
def summary(_: None = Depends(verify_ops_api_key)) -> SummaryResponse:
    # CR-036: the preferred endpoint for Founder Pulse to consume.

    return OpsService.get_summary()
