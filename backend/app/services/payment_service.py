import sqlite3
import time
from datetime import datetime
from typing import Optional

import razorpay
from razorpay.errors import SignatureVerificationError

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService
from app.services.monitoring_event_service import MonitoringEventService
from app.services.subscription_service import SubscriptionService


class PaymentNotConfiguredError(Exception):
    pass


class UnsupportedPlanError(Exception):
    pass


class PaymentGatewayError(Exception):
    pass


class InvalidPaymentSignatureError(Exception):
    pass


class InvalidWebhookSignatureError(Exception):
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

    # REVENUE-004: the only event that grants entitlement — captured means
    # Razorpay has definitively taken the money. payment.failed is handled
    # as a pure no-op (see handle_webhook_event) so an out-of-order/late
    # failed event can never revoke an already-processed captured payment.
    # Any other event (order.paid, refund.*, payment.authorized, ...) is
    # logged and ignored — out of scope for this MVP.
    WEBHOOK_EVENT_PAYMENT_CAPTURED = "payment.captured"
    WEBHOOK_EVENT_PAYMENT_FAILED = "payment.failed"

    @staticmethod
    def _row_factory(cursor, row):
        return {
            col[0]: row[idx]
            for idx, col in enumerate(cursor.description)
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
            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "order_creation_failed"
            )
            raise PaymentGatewayError(
                "Failed to create payment order"
            ) from exc

        LoggerService.info(
            f"Order created receipt={receipt}",
            user_id=user_id
        )

        cls._record_pending_order(user_id, order["id"], plan)

        return {
            "order_id": order["id"],
            "amount": pricing["amount"],
            "currency": pricing["currency"],
            "key_id": settings.RAZORPAY_KEY_ID,
        }

    @classmethod
    def _record_pending_order(
        cls,
        user_id: int,
        razorpay_order_id: str,
        plan: str,
    ) -> None:
        # Best-effort bookkeeping only — the browser-driven /payments/verify
        # path never reads this table, so a failure here must not fail
        # checkout. It only means the webhook/reconciliation safety nets
        # won't be able to resolve this one order back to a user later.

        now = datetime.utcnow().isoformat()

        try:
            connection = DatabaseService.get_connection()
            try:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO pending_orders (
                        razorpay_order_id, user_id, plan, status,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, 'PENDING', ?, ?)
                    """,
                    (razorpay_order_id, user_id, plan, now, now)
                )
                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(
                f"Failed to record pending order "
                f"order_id={razorpay_order_id}: {exc}",
                user_id=user_id
            )

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
            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "invalid_signature"
            )
            raise InvalidPaymentSignatureError(
                "Payment signature verification failed"
            ) from exc
        except Exception as exc:
            LoggerService.error(
                "Payment verification failed: gateway error",
                user_id=user_id
            )
            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "gateway_error"
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
        # concurrent duplicate is guaranteed to lose. A payments row that
        # already exists for this razorpay_payment_id is resolved by
        # _resolve_existing_payment: an idempotent success if it's the same
        # (user, order, plan) — e.g. the webhook and browser paths racing
        # for the same real payment — or a rejected DuplicatePaymentError
        # if any of those differ, which would mean someone is trying to
        # attach an already-captured payment_id to a different user/order.

        existing = cls._find_payment_by_payment_id(razorpay_payment_id)

        if existing is not None:
            return cls._resolve_existing_payment(
                existing, user_id, razorpay_order_id, plan,
                razorpay_payment_id
            )

        now = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

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

            # REVENUE-004: resolves the pending_orders row (if any) as part
            # of the same atomic transaction. Safe no-op (rowcount 0) when
            # there is no matching row — e.g. an order that predates this
            # feature, or whose _record_pending_order insert failed.
            cursor.execute(
                """
                UPDATE pending_orders
                SET status = 'RESOLVED', updated_at = ?
                WHERE razorpay_order_id = ?
                """,
                (now, razorpay_order_id)
            )

            connection.commit()

        except sqlite3.IntegrityError:
            # Lost a concurrent race for this exact razorpay_payment_id —
            # the winning writer's row exists now. Resolve against it the
            # same way a pre-existing row would have been resolved above,
            # instead of unconditionally rejecting.
            connection.rollback()
            connection.close()

            winner = cls._find_payment_by_payment_id(razorpay_payment_id)

            if winner is None:
                # The IntegrityError wasn't the razorpay_payment_id UNIQUE
                # constraint after all (e.g. a foreign-key violation) — no
                # row was ever written, so there is nothing to resolve
                # against. Treat this as a genuine processing failure
                # instead of assuming a winner exists.
                LoggerService.error(
                    f"Payment processing failed after verification: "
                    f"payment_id={razorpay_payment_id}",
                    user_id=user_id
                )

                MonitoringEventService.record_failure(
                    MonitoringEventService.PAYMENT, "processing_failed"
                )

                raise PaymentProcessingError(
                    "Failed to process payment"
                )

            return cls._resolve_existing_payment(
                winner, user_id, razorpay_order_id, plan,
                razorpay_payment_id
            )

        except Exception as exc:
            connection.rollback()
            connection.close()

            LoggerService.error(
                f"Payment processing failed after verification: "
                f"payment_id={razorpay_payment_id}",
                user_id=user_id
            )

            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "processing_failed"
            )

            raise PaymentProcessingError(
                "Failed to process payment"
            ) from exc

        connection.close()

        return SubscriptionService.get_by_user_id(user_id)

    @classmethod
    def _find_payment_by_payment_id(
        cls, razorpay_payment_id: str
    ) -> Optional[dict]:

        connection = DatabaseService.get_connection()
        connection.row_factory = cls._row_factory

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT user_id, razorpay_order_id, plan
                FROM payments
                WHERE razorpay_payment_id = ?
                """,
                (razorpay_payment_id,)
            )
            return cursor.fetchone()
        finally:
            connection.close()

    @classmethod
    def _resolve_existing_payment(
        cls,
        existing: dict,
        user_id: int,
        razorpay_order_id: str,
        plan: str,
        razorpay_payment_id: str,
    ) -> dict:
        # A payments row for this razorpay_payment_id already exists.
        # Same (user, order, plan): an idempotent retry of a payment that
        # was already fully processed elsewhere (webhook, browser, or
        # reconciliation) — return the current entitlement without a
        # second write. Any mismatch is treated as an attempt to attach an
        # already-captured payment_id to a different user/order/plan and
        # rejected, exactly as a straight duplicate always was.
        same_payment = (
            existing["user_id"] == user_id
            and existing["razorpay_order_id"] == razorpay_order_id
            and existing["plan"] == plan
        )

        if not same_payment:
            LoggerService.info(
                f"Duplicate payment verification rejected "
                f"(user/order/plan mismatch): "
                f"payment_id={razorpay_payment_id}",
                user_id=user_id
            )

            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "duplicate_mismatch"
            )

            raise DuplicatePaymentError(
                "Payment has already been processed."
            )

        LoggerService.info(
            f"Idempotent payment verification: payment_id="
            f"{razorpay_payment_id} already processed for this exact "
            f"payment, no new entitlement granted",
            user_id=user_id
        )

        cls._ensure_pending_order_resolved(razorpay_order_id)

        return SubscriptionService.get_by_user_id(user_id)

    @classmethod
    def _ensure_pending_order_resolved(cls, razorpay_order_id: str) -> None:
        # Best-effort, same non-fatal-on-failure contract as
        # _record_pending_order. The row is usually already RESOLVED (the
        # common case) or absent entirely (predates this feature) — both
        # are no-ops.

        now = datetime.utcnow().isoformat()

        try:
            connection = DatabaseService.get_connection()
            try:
                connection.execute(
                    """
                    UPDATE pending_orders
                    SET status = 'RESOLVED', updated_at = ?
                    WHERE razorpay_order_id = ? AND status != 'RESOLVED'
                    """,
                    (now, razorpay_order_id)
                )
                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(
                f"Failed to resolve pending order on idempotent retry "
                f"order_id={razorpay_order_id}: {exc}"
            )

    # ── REVENUE-004: pending-order lookups (webhook + reconciliation) ──

    @classmethod
    def find_pending_order(cls, razorpay_order_id: str) -> Optional[dict]:

        connection = DatabaseService.get_connection()
        connection.row_factory = cls._row_factory

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT razorpay_order_id, user_id, plan, status, created_at
                FROM pending_orders
                WHERE razorpay_order_id = ?
                """,
                (razorpay_order_id,)
            )
            return cursor.fetchone()
        finally:
            connection.close()

    @classmethod
    def list_pending_orders_older_than(cls, cutoff_iso: str) -> list[dict]:

        connection = DatabaseService.get_connection()
        connection.row_factory = cls._row_factory

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT razorpay_order_id, user_id, plan, status, created_at
                FROM pending_orders
                WHERE status = 'PENDING' AND created_at <= ?
                """,
                (cutoff_iso,)
            )
            return cursor.fetchall()
        finally:
            connection.close()

    @classmethod
    def mark_order_abandoned(cls, razorpay_order_id: str) -> None:
        # Guarded on status = 'PENDING' so this can never clobber a row a
        # webhook/browser-verify resolved in the moment between
        # reconciliation reading it and deciding to abandon it.

        now = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()
        try:
            connection.execute(
                """
                UPDATE pending_orders
                SET status = 'ABANDONED', updated_at = ?
                WHERE razorpay_order_id = ? AND status = 'PENDING'
                """,
                (now, razorpay_order_id)
            )
            connection.commit()
        finally:
            connection.close()

    # ── REVENUE-004: webhook signature + event handling ──

    @staticmethod
    def is_webhook_configured() -> bool:

        return bool(settings.RAZORPAY_WEBHOOK_SECRET)

    @classmethod
    def verify_webhook_signature(cls, raw_body: bytes, signature: str) -> None:
        # verify_webhook_signature is a pure HMAC-SHA256(raw_body, secret)
        # check independent of API key auth, so a throwaway unauthenticated
        # Client is fine here — it never calls the network.

        if not cls.is_webhook_configured():
            raise PaymentNotConfiguredError(
                "Razorpay webhook secret is not configured"
            )

        if not signature:
            raise InvalidWebhookSignatureError(
                "Missing webhook signature"
            )

        try:
            razorpay.Client().utility.verify_webhook_signature(
                raw_body.decode("utf-8"),
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET,
            )
        except SignatureVerificationError as exc:
            raise InvalidWebhookSignatureError(
                "Invalid webhook signature"
            ) from exc

    @classmethod
    def handle_webhook_event(cls, payload: dict, event_id: str = "") -> None:
        # Duplicate/out-of-order deliveries of payment.captured are made
        # safe by process_verified_payment's existing razorpay_payment_id
        # UNIQUE constraint — the same protection the browser-driven
        # /payments/verify path already relies on. event_id is logged for
        # traceability only; it is not persisted as a second dedup key.

        event = payload.get("event", "")

        if event == cls.WEBHOOK_EVENT_PAYMENT_CAPTURED:
            cls._handle_payment_captured(payload, event_id)
            return

        if event == cls.WEBHOOK_EVENT_PAYMENT_FAILED:
            LoggerService.info(
                f"Webhook payment.failed received event_id={event_id} "
                f"(no-op: never revokes an existing entitlement)"
            )
            return

        LoggerService.info(
            f"Webhook event ignored: event={event!r} event_id={event_id}"
        )

    @classmethod
    def _handle_payment_captured(cls, payload: dict, event_id: str) -> None:

        try:
            entity = payload["payload"]["payment"]["entity"]
            razorpay_order_id = entity["order_id"]
            razorpay_payment_id = entity["id"]
        except (KeyError, TypeError) as exc:
            LoggerService.error(
                f"Malformed payment.captured webhook payload "
                f"event_id={event_id}: {exc}"
            )
            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "webhook_malformed_payload"
            )
            return

        pending_order = cls.find_pending_order(razorpay_order_id)

        if pending_order is None:
            LoggerService.error(
                f"Webhook payment.captured for unmatched order "
                f"order_id={razorpay_order_id} event_id={event_id}"
            )
            MonitoringEventService.record_failure(
                MonitoringEventService.PAYMENT, "webhook_unmatched_order"
            )
            return

        try:
            cls.process_verified_payment(
                pending_order["user_id"],
                razorpay_order_id,
                razorpay_payment_id,
                pending_order["plan"],
            )
            LoggerService.info(
                f"Webhook payment.captured processed "
                f"order_id={razorpay_order_id} "
                f"payment_id={razorpay_payment_id} event_id={event_id}",
                user_id=pending_order["user_id"]
            )
        except DuplicatePaymentError:
            LoggerService.info(
                f"Webhook payment.captured already processed "
                f"payment_id={razorpay_payment_id} event_id={event_id}",
                user_id=pending_order["user_id"]
            )
