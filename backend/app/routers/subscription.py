from fastapi import APIRouter, Depends

from app.services.subscription_service import SubscriptionService
from app.dependencies import get_current_user


router = APIRouter(
    prefix="/subscription",
    tags=["Subscription"]
)


@router.get("/me")
def get_my_subscription(
    current_user: dict = Depends(get_current_user)
):

    subscription = SubscriptionService.get_by_user_id(
        current_user["id"]
    )

    if not subscription:

        subscription = SubscriptionService.create_default_subscription(
            current_user["id"]
        )

    return {
        "plan": subscription["plan"],
        "status": subscription["status"],
        "creditsRemaining": current_user["credits_remaining"],
    }


@router.post("/mock-upgrade")
def mock_upgrade(
    current_user: dict = Depends(get_current_user)
):

    subscription = SubscriptionService.upgrade_to_pro(
        current_user["id"]
    )

    return {
        "plan": subscription["plan"],
        "status": subscription["status"],
        "creditsRemaining": current_user["credits_remaining"],
    }
