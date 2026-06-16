from fastapi import APIRouter, HTTPException
from app.services.vision_service import VisionService


router = APIRouter(
    prefix="/vision",
    tags=["AI Vision"]
)


@router.post("/analyze")
def analyze_frame(image_path: str):

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