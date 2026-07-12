from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.maintenance_service import MaintenanceService
from app.services.observability_service import ObservabilityService

router = APIRouter(tags=["Observability"])


@router.get("/health")
def health():

    result = ObservabilityService.check_health()
    status_code = 200 if result["status"] == "ok" else 503
    return JSONResponse(
        content=result,
        status_code=status_code
    )


@router.get("/ready")
def ready():

    result = ObservabilityService.check_ready()
    status_code = 200 if result["ready"] else 503
    return JSONResponse(
        content=result,
        status_code=status_code
    )


@router.get("/metrics")
def metrics():

    return ObservabilityService.get_metrics()


@router.get("/maintenance-status")
def maintenance_status():

    return {
        "maintenance": MaintenanceService.is_maintenance_mode()
    }
