from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.health_service import HealthService
from app.services.maintenance_service import MaintenanceService
from app.services.observability_service import ObservabilityService
from app.services.subscription_service import SubscriptionPlan, SubscriptionStatus

# VED-085: failed-job-rate threshold above which the BLOCKERS section
# surfaces a warning. Chosen as a simple, explainable round number — not
# derived from historical data (there isn't enough production history yet
# to fit one).
FAILED_JOB_RATE_WARNING_THRESHOLD = 0.20

# Static, code-reviewed registry of capabilities confirmed to exist in this
# repository (Phase 1 inventory). Deliberately a plain Python structure
# rather than a new DB table or file format — it changes only when a
# developer adds/removes a real capability and reviews the diff, so a
# config file would just be one more place for it to drift from the code
# it describes.
CAPABILITY_REGISTRY: list[dict] = [
    {
        "category": "Product",
        "capabilities": [
            {"name": "Video upload & background job pipeline", "evidence": "backend/app/routers/upload.py, backend/app/routers/pipeline.py"},
            {"name": "Account creation & email verification", "evidence": "backend/app/routers/auth.py, backend/app/services/email_verification_service.py"},
            {"name": "Projects & highlight history", "evidence": "backend/app/routers/projects.py, backend/app/routers/history.py"},
            {"name": "In-app user feedback capture", "evidence": "backend/app/routers/feedback.py"},
        ],
    },
    {
        "category": "AI / Pipeline",
        "capabilities": [
            {"name": "Frame captioning & motion scoring (BLIP + OpenCV)", "evidence": "backend/app/services/vision_service.py"},
            {"name": "Audio transcription (Whisper)", "evidence": "backend/app/services/whisper_service.py"},
            {"name": "Zero-shot frame category scoring (CLIP)", "evidence": "backend/app/services/clip_service.py"},
            {"name": "Multi-factor highlight scoring engine", "evidence": "backend/app/services/scoring/"},
            {"name": "Thumbnail quality scoring: blur, brightness, composition, contrast, and sharpness", "evidence": "backend/app/services/thumbnail/"},
            {"name": "End-to-end pipeline orchestration", "evidence": "backend/app/services/pipeline_service.py"},
        ],
    },
    {
        "category": "Monetization",
        "capabilities": [
            {"name": "Razorpay order creation & payment verification", "evidence": "backend/app/services/payment_service.py, backend/app/routers/payments.py"},
            {"name": "PRO subscription lifecycle (30-day grants, expiry downgrade)", "evidence": "backend/app/services/subscription_service.py"},
            {"name": "Free-credit metering", "evidence": "users.credits_remaining, backend/app/services/auth_service.py"},
        ],
    },
    {
        "category": "Analytics",
        "capabilities": [
            {"name": "Client-side product analytics (PostHog)", "evidence": "frontend/services/analytics.ts, frontend/instrumentation-client.ts"},
            {"name": "In-app job/user metrics endpoint", "evidence": "backend/app/services/observability_service.py"},
        ],
    },
    {
        "category": "Operations",
        "capabilities": [
            {"name": "Health / readiness / metrics endpoints", "evidence": "backend/app/routers/observability.py, backend/app/services/health_service.py"},
            {"name": "Maintenance mode & deployment drain", "evidence": "backend/app/services/maintenance_service.py, scripts/maintenance.sh"},
            {"name": "Database & storage backup/restore", "evidence": "scripts/backup.sh, scripts/restore.sh"},
            {"name": "CI build verification", "evidence": ".github/workflows/build.yml"},
        ],
    },
    {
        "category": "Growth / Export",
        "capabilities": [
            {"name": "Vertical (9:16) reel export for Shorts/Reels/TikTok", "evidence": "backend/app/services/reel_service.py"},
            {"name": "Caption burn-in", "evidence": "backend/app/services/caption_service.py"},
            {"name": "Per-platform social export metadata", "evidence": "backend/app/services/social_export_service.py"},
            {"name": "Homepage product trust proof", "evidence": "frontend/app/page.tsx (GROW-004A)"},
        ],
    },
    {
        "category": "Engineering",
        "capabilities": [
            {"name": "Service-layer backend architecture", "evidence": "backend/app/services/"},
            {"name": "SQLite schema with guarded inline migrations", "evidence": "backend/app/services/database_service.py"},
            {"name": "Endpoint rate limiting", "evidence": "backend/app/services/rate_limit_service.py"},
            {"name": "Interrupted-job reconciliation on restart", "evidence": "backend/app/services/job_service.py:reconcile_interrupted_jobs"},
        ],
    },
]

# VED-086: static integration-readiness registry for the Social Pulse
# section. Not DB-backed and not wired to any external API — flipping a
# platform's status to "connected" (and adding real fields like followers
# or last_synced_at) is the intended VED-087 Social Intelligence Hub
# integration point, behind this same summary key.
SOCIAL_INTEGRATIONS: list[dict] = [
    {"platform": "Instagram", "status": "not_connected"},
    {"platform": "YouTube", "status": "not_connected"},
    {"platform": "LinkedIn", "status": "not_connected"},
    {"platform": "X", "status": "not_connected"},
]


class MissionControlService:

    @classmethod
    def get_summary(cls) -> dict:

        maintenance_on = MaintenanceService.is_maintenance_mode()
        health = ObservabilityService.check_health()
        metrics = cls._get_live_metrics()
        distribution = cls._get_distribution()
        release = cls._get_release_info()

        return {
            "production_health": {
                "status": health["status"],
                "database": health["database"],
                "ffmpeg": health["ffmpeg"],
                "uptime_seconds": health["uptime_seconds"],
                "maintenance_mode": maintenance_on,
                "environment": health["environment"],
            },
            "live_metrics": metrics,
            "distribution": distribution,
            "capability_registry": CAPABILITY_REGISTRY,
            "blockers": cls._get_blockers(metrics, distribution, maintenance_on),
            "release": release,
            "weekly_activity": cls._get_weekly_activity(),
            "social_integrations": SOCIAL_INTEGRATIONS,
        }

    @classmethod
    def _get_live_metrics(cls) -> dict:

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()

        cls._expire_stale_pro_subscriptions(cursor)

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE email_verified = 1"
        )
        verified_users = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(DISTINCT user_id) FROM jobs WHERE user_id IS NOT NULL"
        )
        users_with_jobs = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id) FROM jobs
            WHERE user_id IS NOT NULL AND status = 'completed'
            """
        )
        users_with_completed_jobs = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT user_id FROM jobs
                WHERE user_id IS NOT NULL
                GROUP BY user_id
                HAVING COUNT(*) >= 2
            )
            """
        )
        repeat_users = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
            FROM jobs
            """
        )
        total_jobs, completed_jobs, failed_jobs = cursor.fetchone()

        cursor.execute(
            """
            SELECT COUNT(*) FROM subscriptions
            WHERE plan = ? AND status = ?
            """,
            (SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE),
        )
        active_pro_users = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'PROCESSED'"
        )
        processed_payments = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM feedback")
        distinct_feedback_users = cursor.fetchone()[0] or 0

        connection.close()

        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "users_with_jobs": users_with_jobs,
            "users_with_completed_jobs": users_with_completed_jobs,
            "repeat_users": repeat_users,
            "total_jobs": total_jobs or 0,
            "completed_jobs": completed_jobs or 0,
            "failed_jobs": failed_jobs or 0,
            "active_pro_users": active_pro_users,
            "processed_payments": processed_payments,
            "distinct_feedback_users": distinct_feedback_users,
        }

    @classmethod
    def _expire_stale_pro_subscriptions(cls, cursor) -> None:
        # Same downgrade rule SubscriptionService.get_by_user_id applies
        # per-user on read, run once here so the active_pro_users count
        # reflects subscriptions whose expires_at has already lapsed but
        # haven't been read (and self-healed) individually yet.

        now = datetime.now(timezone.utc).isoformat()

        cursor.execute(
            """
            UPDATE subscriptions
            SET plan = ?, status = ?, updated_at = ?
            WHERE plan = ?
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            (
                SubscriptionPlan.FREE,
                SubscriptionStatus.EXPIRED,
                now,
                SubscriptionPlan.PRO,
                now,
            ),
        )
        cursor.connection.commit()

    @classmethod
    def _get_distribution(cls) -> dict:

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN credits_remaining <= 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN credits_remaining BETWEEN 1 AND 2 THEN 1 ELSE 0 END),
                SUM(CASE WHEN credits_remaining >= 3 THEN 1 ELSE 0 END)
            FROM users
            """
        )
        exhausted, low, healthy = cursor.fetchone()

        cursor.execute(
            """
            SELECT COUNT(*) FROM jobs
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            """
        )
        job_counts_per_user = [row[0] for row in cursor.fetchall()]

        connection.close()

        jobs_per_user_buckets = {"1": 0, "2-3": 0, "4-5": 0, "6+": 0}
        for count in job_counts_per_user:
            if count == 1:
                jobs_per_user_buckets["1"] += 1
            elif 2 <= count <= 3:
                jobs_per_user_buckets["2-3"] += 1
            elif 4 <= count <= 5:
                jobs_per_user_buckets["4-5"] += 1
            else:
                jobs_per_user_buckets["6+"] += 1

        return {
            "credit_breakdown": {
                "exhausted": exhausted or 0,
                "low": low or 0,
                "healthy": healthy or 0,
            },
            "jobs_per_user": jobs_per_user_buckets,
        }

    @classmethod
    def _get_weekly_activity(cls) -> list[dict]:
        # VED-086: jobs.created_at is stored as a naive UTC ISO string
        # everywhere in this schema (no per-user/server timezone is ever
        # recorded), so "day" here means UTC calendar day — the only
        # grouping that's unambiguous given the data we actually have.

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                date(created_at) AS day,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
            FROM jobs
            WHERE created_at IS NOT NULL
              AND date(created_at) >= date('now', '-6 days')
              AND date(created_at) <= date('now')
            GROUP BY day
            """
        )
        rows_by_day = {
            day: {"total": total, "completed": completed, "failed": failed}
            for day, total, completed, failed in cursor.fetchall()
        }

        connection.close()

        today = datetime.now(timezone.utc).date()
        return [
            {
                "date": day.isoformat(),
                **rows_by_day.get(day.isoformat(), {"total": 0, "completed": 0, "failed": 0}),
            }
            for day in (today - timedelta(days=offset) for offset in range(6, -1, -1))
        ]

    @classmethod
    def _get_blockers(
        cls,
        metrics: dict,
        distribution: dict,
        maintenance_on: bool,
    ) -> list[dict]:

        blockers: list[dict] = []

        if maintenance_on:
            blockers.append({
                "id": "maintenance_mode_on",
                "severity": "warning",
                "message": "Maintenance mode is currently ON — uploads and pipeline starts are blocked.",
            })

        if metrics["distinct_feedback_users"] == 0:
            blockers.append({
                "id": "zero_feedback_users",
                "severity": "info",
                "message": "No user feedback has been collected yet.",
            })

        total_jobs = metrics["total_jobs"]
        failed_jobs = metrics["failed_jobs"]
        if total_jobs > 0:
            failure_rate = failed_jobs / total_jobs
            if failure_rate > FAILED_JOB_RATE_WARNING_THRESHOLD:
                blockers.append({
                    "id": "elevated_failed_job_rate",
                    "severity": "warning",
                    "message": (
                        f"Elevated failed job rate: {round(failure_rate * 100, 1)}% "
                        f"({failed_jobs}/{total_jobs})."
                    ),
                })

        if metrics["processed_payments"] == 0:
            blockers.append({
                "id": "no_processed_payments",
                "severity": "info",
                "message": "No payments have been processed yet.",
            })

        exhausted = distribution["credit_breakdown"]["exhausted"]
        if exhausted > 0:
            blockers.append({
                "id": "users_exhausting_credits",
                "severity": "info",
                "message": f"{exhausted} user(s) have exhausted their free credits.",
            })

        return blockers

    @classmethod
    def _get_release_info(cls) -> dict:

        build = HealthService.get_app_version()

        return {
            "app_version": settings.APP_VERSION,
            "git_commit": build.get("git_commit", "unknown"),
            "git_tag": build.get("git_tag", "unknown"),
            "ci": {
                "workflow": "Build Verification (.github/workflows/build.yml)",
                "note": (
                    "Build/compile check only on push and PR to main — "
                    "no deploy or release-tagging automation exists in this repo."
                ),
            },
        }
