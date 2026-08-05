from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import require_admin
from app.services.alert_engine_service import AlertEngineService
from app.services.health_engine_service import HealthEngineService
from app.services.health_history_service import HealthHistoryService

# VED-P1-002: admin-only Production Monitoring surface backing the
# /admin/health page. Same auth pattern as mission_control.py
# (require_admin, re-checked per request), a separate prefix so it is
# additive rather than a redesign of Mission Control.
router = APIRouter(
    prefix="/admin/health",
    tags=["Health Monitoring"],
)


@router.get("/summary")
def summary(
    current_user: dict = Depends(require_admin)
):

    report = HealthEngineService.evaluate()

    return {
        **report,
        "open_alerts": AlertEngineService.get_open_alerts(),
    }


@router.get("/history")
def history(
    range: str = Query("today", pattern="^(today|yesterday|7d|30d)$"),
    current_user: dict = Depends(require_admin)
):

    return HealthHistoryService.get_history(range)


@router.get("/alerts")
def alerts(
    resolved: Optional[bool] = Query(None),
    current_user: dict = Depends(require_admin)
):

    return {"alerts": AlertEngineService.list_alerts(resolved=resolved)}
