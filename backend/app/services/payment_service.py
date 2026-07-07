import time

import razorpay
from razorpay.errors import SignatureVerificationError

from app.config.config import settings
from app.services.logger_service import LoggerService


class PaymentNotConfiguredError(Exception):
    pass


class UnsupportedPlanError(Exception):
    pass


class PaymentGatewayError(Exception):
    pass


class InvalidPaymentSignatureError(Exception):
    pass


class PaymentService:

    _client: razorpay.Client | None = None

    PLAN_PRICING: dict[str, dict[str, str | int]] = {
        "pro": {
            "amount": 29900,
            "currency": "INR",
            "interval": "monthly",
        },
    }

    @classmethod
    def get_client(cls) -> razorpay.Client | None:

        if not cls.is_configured():
            return None

        if cls._client is None:
            cls._client = razorpay.Client(
                auth=(
                    settings.RAZORPAY_KEY_ID,
                    settings.RAZORPAY_KEY_SECRET
                )
            )

        return cls._client

    @staticmethod
    def is_configured() -> bool:

        return bool(
            settings.RAZORPAY_KEY_ID
            and settings.RAZORPAY_KEY_SECRET
        )

    @classmethod
    def create_order(cls, user_id: int, plan: str) -> dict[str, str | int]:

        if not cls.is_configured():
            raise PaymentNotConfiguredError(
                "Razorpay is not configured"
            )

        pricing = cls.PLAN_PRICING.get(plan)

        if pricing is None:
            raise UnsupportedPlanError(
                f"Unsupported plan: {plan}"
            )

        client = cls.get_client()
        receipt = f"vedzovi-pro-{user_id}-{int(time.time())}"

        try:
            order = client.order.create({
                "amount": pricing["amount"],
                "currency": pricing["currency"],
                "receipt": receipt,
            })
        except Exception as exc:
            LoggerService.error(
                "Order creation failed",
                user_id=user_id
            )
            raise PaymentGatewayError(
                "Failed to create payment order"
            ) from exc

        LoggerService.info(
            f"Order created receipt={receipt}",
            user_id=user_id
        )

        return {
            "order_id": order["id"],
            "amount": pricing["amount"],
            "currency": pricing["currency"],
            "key_id": settings.RAZORPAY_KEY_ID,
        }

    @classmethod
    def verify_payment(
        cls,
        user_id: int,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> None:

        if not cls.is_configured():
            raise PaymentNotConfiguredError(
                "Razorpay is not configured"
            )

        LoggerService.info(
            "Payment verification started",
            user_id=user_id
        )

        client = cls.get_client()

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except SignatureVerificationError as exc:
            LoggerService.error(
                "Payment verification failed: invalid signature",
                user_id=user_id
            )
            raise InvalidPaymentSignatureError(
                "Payment signature verification failed"
            ) from exc
        except Exception as exc:
            LoggerService.error(
                "Payment verification failed: gateway error",
                user_id=user_id
            )
            raise PaymentGatewayError(
                "Failed to verify payment"
            ) from exc

        LoggerService.info(
            "Payment verification succeeded",
            user_id=user_id
        )
