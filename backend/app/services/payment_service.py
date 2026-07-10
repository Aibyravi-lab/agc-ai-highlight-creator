import sqlite3
import time
from datetime import datetime

import razorpay
from razorpay.errors import SignatureVerificationError

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService
from app.services.subscription_service import SubscriptionService


class PaymentNotConfiguredError(Exception):
    pass


class UnsupportedPlanError(Exception):
    pass


class PaymentGatewayError(Exception):
    pass


class InvalidPaymentSignatureError(Exception):
    pass


class DuplicatePaymentError(Exception):
    pass


class PaymentProcessingError(Exception):
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

    @classmethod
    def process_verified_payment(
        cls,
        user_id: int,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        plan: str,
    ) -> dict:
        # The razorpay_payment_id UNIQUE constraint is the actual replay
        # guard: it makes the INSERT below the single point where a
        # concurrent duplicate is guaranteed to lose.

        now = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM payments WHERE razorpay_payment_id = ?",
            (razorpay_payment_id,)
        )

        already_processed = cursor.fetchone() is not None

        if already_processed:
            connection.close()

            LoggerService.info(
                f"Duplicate payment verification rejected: "
                f"payment_id={razorpay_payment_id}",
                user_id=user_id
            )

            raise DuplicatePaymentError(
                "Payment has already been processed."
            )

        try:
            cursor.execute(
                """
                INSERT INTO payments (
                    user_id, razorpay_order_id, razorpay_payment_id,
                    plan, status, created_at, processed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    razorpay_order_id,
                    razorpay_payment_id,
                    plan,
                    "PROCESSED",
                    now,
                    now,
                )
            )

            SubscriptionService.upgrade_to_pro_in_transaction(
                connection,
                user_id
            )

            connection.commit()

        except sqlite3.IntegrityError:
            connection.rollback()

            LoggerService.info(
                f"Duplicate payment verification rejected: "
                f"payment_id={razorpay_payment_id}",
                user_id=user_id
            )

            raise DuplicatePaymentError(
                "Payment has already been processed."
            ) from None

        except Exception as exc:
            connection.rollback()

            LoggerService.error(
                f"Payment processing failed after verification: "
                f"payment_id={razorpay_payment_id}",
                user_id=user_id
            )

            raise PaymentProcessingError(
                "Failed to process payment"
            ) from exc

        finally:
            connection.close()

        return SubscriptionService.get_by_user_id(user_id)
