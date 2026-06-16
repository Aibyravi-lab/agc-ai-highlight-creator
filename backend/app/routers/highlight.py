from fastapi import APIRouter, HTTPException
from app.services.highlight_service import HighlightService


router = APIRouter(
    prefix="/highlight",
    tags=["Highlight Detection"]
)


@router.post("/analyze")
def analyze_highlight(description: str):

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