from fastapi import APIRouter, HTTPException, Depends
from app.services.vision_service import VisionService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/vision",
    tags=["AI Vision"]
)


@router.post("/analyze")
def analyze_frame(
    image_path: str,
    current_user: dict = Depends(get_current_user)
):

    try:
        result = VisionService.analyze_frame(image_path)

        return {
            "success": True,
            "data": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )