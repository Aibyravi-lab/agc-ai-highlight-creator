from fastapi import APIRouter, Depends

from app.services.history_service import (
    HistoryService
)
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/history",
    tags=["History"]
)


@router.get("/")
def get_history(
    current_user: dict = Depends(get_current_user)
):

    print(
        f"\n[HISTORY DEBUG] Current user: "
        f"{current_user['id']}"
    )

    history = (
        HistoryService.get_history(
            user_id=current_user["id"]
        )
    )

    return {
        "success": True,
        "data": history
    }