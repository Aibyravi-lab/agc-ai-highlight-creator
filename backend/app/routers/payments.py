from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config.config import settings
from app.dependencies import get_current_user
from app.services.payment_service import (
    DuplicatePaymentError,
    InvalidPaymentSignatureError,
    PaymentGatewayError,
    PaymentNotConfiguredError,
    PaymentProcessingError,
    PaymentService,
    UnsupportedPlanError,
)
from app.services.rate_limit_service import RateLimitService

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


class CreateOrderRequest(BaseModel):
    plan: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.get("/health")
def health():

    return {
        "status": "ok",
        "configured": PaymentService.is_configured()
    }


@router.post("/create-order")
def create_order(
    body: CreateOrderRequest,
    current_user: dict = Depends(get_current_user)
):

    try:
        return PaymentService.create_order(current_user["id"], body.plan)

    except PaymentNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc

    except UnsupportedPlanError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except PaymentGatewayError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc


@router.post("/verify")
def verify_payment(
    body: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user)
):

    user_id = current_user["id"]

    if RateLimitService.is_rate_limited(
        key=f"user:{user_id}",
        endpoint="payment_verify",
        max_attempts=settings.PAYMENT_VERIFY_RATE_LIMIT_MAX_PER_MINUTE,
        window_seconds=60
    ):

        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    try:
        PaymentService.verify_payment(
            user_id,
            body.razorpay_order_id,
            body.razorpay_payment_id,
            body.razorpay_signature,
        )

    except InvalidPaymentSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc)
        ) from exc

    except PaymentNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc

    except PaymentGatewayError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc

    try:
        subscription = PaymentService.process_verified_payment(
            user_id,
            body.razorpay_order_id,
            body.razorpay_payment_id,
            "pro",
        )

    except DuplicatePaymentError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc)
        ) from exc

    except PaymentProcessingError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc

    return {
        "success": True,
        "plan": subscription["plan"],
        "status": subscription["status"],
    }
