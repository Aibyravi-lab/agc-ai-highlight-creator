from fastapi import APIRouter, HTTPException, Depends
from app.services.highlight_service import HighlightService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/highlight",
    tags=["Highlight Detection"]
)


@router.post("/analyze")
def analyze_highlight(
    description: str,
    current_user: dict = Depends(get_current_user)
):

    try:
        result = HighlightService.analyze_description(description)

        return {
            "success": True,
            "data": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )