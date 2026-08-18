import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config.config import settings
from app.dependencies import get_current_user
from app.services.payment_service import (
    DuplicatePaymentError,
    InvalidPaymentSignatureError,
    InvalidWebhookSignatureError,
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

    user_id = current_user["id"]

    if RateLimitService.is_rate_limited(
        key=f"user:{user_id}",
        endpoint="payment_create_order",
        max_attempts=settings.PAYMENT_CREATE_ORDER_RATE_LIMIT_MAX_PER_MINUTE,
        window_seconds=60
    ):

        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    try:
        return PaymentService.create_order(user_id, body.plan)

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


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    # REVENUE-004: server-to-server callback from Razorpay — it cannot
    # carry a Vedzovi JWT, so authenticity rests entirely on the HMAC
    # signature below, verified over the exact raw bytes Razorpay sent
    # (Razorpay's own docs: do not parse/re-cast the body before verifying).

    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    event_id = request.headers.get("X-Razorpay-Event-Id", "")

    try:
        PaymentService.verify_webhook_signature(raw_body, signature)

    except InvalidWebhookSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc)
        ) from exc

    except PaymentNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc)
        ) from exc

    try:
        payload = json.loads(raw_body)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload"
        ) from exc

    try:
        PaymentService.handle_webhook_event(payload, event_id)

    except PaymentProcessingError as exc:
        # Transient processing failure (e.g. a busy DB) — a 5xx lets
        # Razorpay's own retry-with-backoff mechanism recover it.
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        ) from exc

    return {"status": "ok"}
