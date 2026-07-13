from fastapi import APIRouter, Depends

from app.dependencies import require_admin
from app.services.mission_control_service import MissionControlService

router = APIRouter(
    prefix="/admin/mission-control",
    tags=["Mission Control"],
)


@router.get("/summary")
def summary(
    current_user: dict = Depends(require_admin)
):

    return MissionControlService.get_summary()
