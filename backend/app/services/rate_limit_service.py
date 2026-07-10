from datetime import datetime, timedelta

from app.services.database_service import DatabaseService


class RateLimitService:
    """
    Generic sliding-window rate limiter shared by every rate-limited
    endpoint (AGC-069). Generalizes the per-IP throttle introduced in
    AGC-063.6 (PasswordResetService.is_ip_throttled): count attempts for
    a (key, endpoint) pair within a trailing window, record the attempt
    only if it isn't already over the limit, and reject once at capacity.
    A "key" is caller-supplied and can be an IP address (anonymous
    endpoints) or a "user:<id>" string (authenticated endpoints) — the
    limiter itself is scope-agnostic.
    """

    @classmethod
    def is_rate_limited(
        cls,
        key: str,
        endpoint: str,
        max_attempts: int,
        window_seconds: int
    ) -> bool:

        now = datetime.utcnow()

        window_start = now - timedelta(seconds=window_seconds)

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM rate_limit_attempts
            WHERE key_value = ? AND endpoint = ? AND created_at > ?
            """,
            (key, endpoint, window_start.isoformat())
        )

        count = cursor.fetchone()[0]

        if count >= max_attempts:

            connection.close()

            return True

        cursor.execute(
            """
            INSERT INTO rate_limit_attempts (
                key_value, endpoint, created_at
            )
            VALUES (?, ?, ?)
            """,
            (key, endpoint, now.isoformat())
        )

        connection.commit()

        connection.close()

        return False
