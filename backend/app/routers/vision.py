from fastapi import APIRouter, HTTPException, Depends
from app.services.logger_service import LoggerService
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
        # VED-P1-018-B: deferred -- VisionService imports transformers/cv2
        # at module scope; importing it here keeps it out of app.main's
        # import path (see the P1-018-B profiling report). The route
        # registers eagerly (needed for /health etc. to come up); the
        # first real /vision/analyze call pays this import once.
        from app.services.vision_service import VisionService

        result = VisionService.analyze_frame(image_path)

        return {
            "success": True,
            "data": result
        }

    except Exception as error:
        LoggerService.error(
            f"Vision analysis failed: {error}"
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error."
            }
        )