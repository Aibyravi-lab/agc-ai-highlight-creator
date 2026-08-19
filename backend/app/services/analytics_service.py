from concurrent.futures import ThreadPoolExecutor

import requests

from app.config.config import settings
from app.services.logger_service import LoggerService


class AnalyticsService:
    """VED-ANALYTICS-002: server-side PostHog capture for events that must
    be tied to an authoritative backend state transition rather than a
    client-side observation. Dispatched on a small dedicated executor so a
    slow/failed PostHog call never blocks the caller (a pipeline worker
    thread or the startup reconciliation pass) — analytics is always
    best-effort here, matching frontend/services/analytics.ts's own
    try/catch-and-swallow posture.
    """

    _executor = ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="analytics"
    )

    CAPTURE_TIMEOUT_SECONDS = 5

    @classmethod
    def capture_highlights_generated(
        cls,
        *,
        user_id: int,
        job_id: str,
        highlights_found: int | None = None
    ) -> None:

        if not settings.POSTHOG_API_KEY or not settings.POSTHOG_HOST:
            # Mirrors frontend/instrumentation-client.ts's own
            # `if (key && host)` guard — unconfigured means disabled, not
            # an error, so local/dev/CI never attempts a real network call.
            return

        cls._executor.submit(
            cls._send_highlights_generated,
            user_id,
            job_id,
            highlights_found
        )

    @classmethod
    def _send_highlights_generated(
        cls,
        user_id: int,
        job_id: str,
        highlights_found: int | None
    ) -> None:

        try:

            properties = {
                "job_id": job_id,
                "$lib": "agc-backend"
            }

            if highlights_found is not None:
                properties["highlights_found"] = highlights_found

            requests.post(
                f"{settings.POSTHOG_HOST}/capture/",
                json={
                    "api_key": settings.POSTHOG_API_KEY,
                    "event": "Highlights Generated",
                    # Same distinct_id convention as the frontend's
                    # identify() call (docs/ANALYTICS_FUNNEL.md) — the
                    # backend integer user_id as a string, so this lands
                    # on the same PostHog person timeline.
                    "distinct_id": str(user_id),
                    "properties": properties
                },
                timeout=cls.CAPTURE_TIMEOUT_SECONDS
            )

        except Exception as error:

            LoggerService.error(
                "event=analytics_capture_failed "
                f"analytics_event=Highlights Generated job_id={job_id} "
                f"error={error}",
                job_id=job_id,
                user_id=user_id
            )

    @classmethod
    def capture_payment_success(
        cls,
        *,
        user_id: int,
        plan: str,
        payment_id: str
    ) -> None:
        # VED-ANALYTICS-003: same disabled-when-unconfigured guard as
        # capture_highlights_generated — no PostHog call attempted unless
        # both settings are present.

        if not settings.POSTHOG_API_KEY or not settings.POSTHOG_HOST:
            return

        cls._executor.submit(
            cls._send_payment_success,
            user_id,
            plan,
            payment_id
        )

    @classmethod
    def _send_payment_success(
        cls,
        user_id: int,
        plan: str,
        payment_id: str
    ) -> None:

        try:

            requests.post(
                f"{settings.POSTHOG_HOST}/capture/",
                json={
                    "api_key": settings.POSTHOG_API_KEY,
                    "event": "Payment Success",
                    "distinct_id": str(user_id),
                    "properties": {
                        # Deliberately excludes razorpay_order_id,
                        # razorpay_payment_id, signature, and email — only
                        # the plan is safe/useful for revenue analytics.
                        "plan": plan,
                        "$lib": "agc-backend"
                    }
                },
                timeout=cls.CAPTURE_TIMEOUT_SECONDS
            )

        except Exception as error:

            LoggerService.error(
                "event=analytics_capture_failed "
                f"analytics_event=Payment Success payment_id={payment_id} "
                f"error={error}",
                user_id=user_id
            )

    # -- VED-ANALYTICS-005: backend-authoritative pipeline lifecycle -------
    #
    # Upload Started/Completed, Pipeline Started/Completed/Failed used to be
    # tracked only from frontend/hooks/usePipeline.ts, which depends on the
    # originating browser tab staying open for the whole upload/processing
    # duration — the same undercounting flaw VED-ANALYTICS-002 fixed for
    # Highlights Generated. Each event below is dual-tracked under its
    # existing legacy snake_case name and PascalCase name (except
    # "pipeline_failed", which never had a PascalCase counterpart) so no
    # existing PostHog dashboard/insight built on either name breaks.

    @classmethod
    def _dispatch(cls, target, *args) -> None:

        if not settings.POSTHOG_API_KEY or not settings.POSTHOG_HOST:
            return

        cls._executor.submit(target, *args)

    @classmethod
    def _post(
        cls,
        *,
        event: str,
        user_id: int,
        properties: dict,
        job_id: str | None = None
    ) -> None:

        try:

            requests.post(
                f"{settings.POSTHOG_HOST}/capture/",
                json={
                    "api_key": settings.POSTHOG_API_KEY,
                    "event": event,
                    "distinct_id": str(user_id),
                    "properties": properties
                },
                timeout=cls.CAPTURE_TIMEOUT_SECONDS
            )

        except Exception as error:

            LoggerService.error(
                "event=analytics_capture_failed "
                f"analytics_event={event} job_id={job_id} error={error}",
                job_id=job_id,
                user_id=user_id
            )

    @classmethod
    def capture_upload_started(cls, *, user_id: int) -> None:

        cls._dispatch(cls._send_upload_started, user_id)

    @classmethod
    def _send_upload_started(cls, user_id: int) -> None:

        properties = {"$lib": "agc-backend"}

        cls._post(event="upload_started", user_id=user_id, properties=properties)
        cls._post(event="Upload Started", user_id=user_id, properties=properties)

    @classmethod
    def capture_upload_completed(cls, *, user_id: int) -> None:

        cls._dispatch(cls._send_upload_completed, user_id)

    @classmethod
    def _send_upload_completed(cls, user_id: int) -> None:

        cls._post(
            event="upload_completed",
            user_id=user_id,
            properties={"$lib": "agc-backend"}
        )

        cls._post(
            event="Upload Completed",
            user_id=user_id,
            # Matches the retired frontend call site's $set — idempotent
            # person-property flag, safe to resend on every completion.
            properties={
                "$lib": "agc-backend",
                "$set": {"first_upload_completed": True}
            }
        )

    @classmethod
    def capture_pipeline_started(cls, *, user_id: int, job_id: str) -> None:

        cls._dispatch(cls._send_pipeline_started, user_id, job_id)

    @classmethod
    def _send_pipeline_started(cls, user_id: int, job_id: str) -> None:

        properties = {"job_id": job_id, "$lib": "agc-backend"}

        cls._post(
            event="pipeline_started",
            user_id=user_id,
            properties=properties,
            job_id=job_id
        )

        cls._post(
            event="Pipeline Started",
            user_id=user_id,
            properties=properties,
            job_id=job_id
        )

    @classmethod
    def capture_pipeline_completed(
        cls,
        *,
        user_id: int,
        job_id: str,
        processing_time_seconds: float | None = None
    ) -> None:

        cls._dispatch(
            cls._send_pipeline_completed,
            user_id,
            job_id,
            processing_time_seconds
        )

    @classmethod
    def _send_pipeline_completed(
        cls,
        user_id: int,
        job_id: str,
        processing_time_seconds: float | None
    ) -> None:

        cls._post(
            event="pipeline_completed",
            user_id=user_id,
            properties={"job_id": job_id, "$lib": "agc-backend"},
            job_id=job_id
        )

        pascal_properties = {"job_id": job_id, "$lib": "agc-backend"}

        if processing_time_seconds is not None:
            pascal_properties["processing_time_seconds"] = processing_time_seconds

        cls._post(
            event="Pipeline Completed",
            user_id=user_id,
            properties=pascal_properties,
            job_id=job_id
        )

    @classmethod
    def capture_pipeline_failed(cls, *, user_id: int, job_id: str) -> None:

        cls._dispatch(cls._send_pipeline_failed, user_id, job_id)

    @classmethod
    def _send_pipeline_failed(cls, user_id: int, job_id: str) -> None:

        # No raw error/exception text is ever included — only the terminal
        # status, matching the retired frontend pipeline_failed call site's
        # own "job.error is intentionally omitted" convention.
        cls._post(
            event="pipeline_failed",
            user_id=user_id,
            properties={
                "job_id": job_id,
                "status": "failed",
                "$lib": "agc-backend"
            },
            job_id=job_id
        )
