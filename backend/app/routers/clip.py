from fastapi import APIRouter, HTTPException, Depends
from app.services.clip_service import ClipService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/clip",
    tags=["CLIP AI"]
)


@router.post("/highlight-check")
def check_highlight(
    image_path: str,
    current_user: dict = Depends(get_current_user)
):

    try:
        result = ClipService.get_highlight_result(
            image_path
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/analyze")
def analyze_image(
    image_path: str,
    current_user: dict = Depends(get_current_user)
):

    try:
        result = ClipService.analyze_frame(
            image_path
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )