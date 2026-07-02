from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.services.feedback_service import FeedbackService

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"]
)


class FeedbackSubmit(BaseModel):
    project_id: Optional[int] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    thumbs: Optional[str] = Field(None, pattern="^(up|down)$")
    comment: Optional[str] = Field(None, max_length=2000)


@router.post("")
def submit_feedback(
    body: FeedbackSubmit,
    current_user: dict = Depends(get_current_user),
):

    feedback = FeedbackService.submit(
        user_id=current_user["id"],
        project_id=body.project_id,
        rating=body.rating,
        thumbs=body.thumbs,
        comment=body.comment,
    )

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
