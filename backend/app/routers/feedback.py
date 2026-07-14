from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_current_user
from app.services.feedback_service import (
    DuplicateFeedbackError,
    FeedbackService,
    ProjectNotFoundError,
)

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"]
)

ImprovementArea = Literal[
    "highlight_selection",
    "clip_timing",
    "processing_speed",
    "captions",
    "other",
]


class FeedbackSubmit(BaseModel):
    project_id: Optional[int] = None
    # GROW-005: 1=Bad, 2=Okay, 3=Good, 4=Great — see FeedbackService.RATING_LABELS.
    # strict=True so a JSON boolean isn't silently coerced into 0/1 (bool is
    # an int subclass in Python; pydantic's default lax mode would accept it).
    rating: Optional[int] = Field(None, ge=1, le=4, strict=True)
    thumbs: Optional[str] = Field(None, pattern="^(up|down)$")
    improvement_area: Optional[ImprovementArea] = None
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator("comment")
    @classmethod
    def _trim_comment(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


@router.post("")
def submit_feedback(
    body: FeedbackSubmit,
    current_user: dict = Depends(get_current_user),
):

    try:
        feedback = FeedbackService.submit(
            user_id=current_user["id"],
            project_id=body.project_id,
            rating=body.rating,
            thumbs=body.thumbs,
            improvement_area=body.improvement_area,
            comment=body.comment,
        )
    except DuplicateFeedbackError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "success": True,
        "data": feedback
    }


@router.get("")
def list_feedback(
    current_user: dict = Depends(get_current_user),
):

    items = FeedbackService.get_all(
        user_id=current_user["id"]
    )

    return {
        "success": True,
        "count": len(items),
        "data": items
    }


@router.delete("/{feedback_id}")
def delete_feedback(
    feedback_id: int,
    current_user: dict = Depends(get_current_user),
):

    deleted = FeedbackService.delete(
        user_id=current_user["id"],
        feedback_id=feedback_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found"
        )

    return {
        "success": True,
        "message": "Feedback deleted"
    }
