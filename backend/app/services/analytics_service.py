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
