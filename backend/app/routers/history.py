from fastapi import APIRouter

from app.services.history_service import (
    HistoryService
)

router = APIRouter(
    prefix="/history",
    tags=["History"]
)


@router.get("/")
def get_history():

    history = (
        HistoryService.get_history()
    )

    return {
        "success": True,
        "data": history
    }