import os
import secrets

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


_JWT_SECRET_KEY_ENV = os.getenv("JWT_SECRET_KEY")

if not _JWT_SECRET_KEY_ENV and os.getenv("ENVIRONMENT", "development") == "production":
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. A persistent secret is required when "
        "ENVIRONMENT=production — falling back to a randomly generated key "
        "would invalidate every issued session on each restart. "
        "Set JWT_SECRET_KEY in backend/.env (see .env.example)."
    )

if not _JWT_SECRET_KEY_ENV:
    print(
        "WARNING: JWT_SECRET_KEY not set — using a random per-process secret. "
        "All existing sessions will be invalidated on restart. "
        "Set JWT_SECRET_KEY in backend/.env for persistent sessions (see .env.example)."
    )


# VED-OPS-001: dedicated, customer-auth-independent key for the internal
# Operations API. Unlike JWT_SECRET_KEY, there is no random fallback and no
# startup hard-fail here: verify_ops_api_key already rejects every request
# when this is unset (fail-closed), so a missing key just means the ops
# surface is disabled, not that the whole app can't start.
_OPS_API_KEY_ENV = os.getenv("OPS_API_KEY")

if not _OPS_API_KEY_ENV:
    print(
        "WARNING: OPS_API_KEY not set — the internal Operations API "
        "(/api/v1/ops/*) will reject all requests. "
        "Set OPS_API_KEY in backend/.env to enable it (see .env.example)."
    )


class Settings(BaseSettings):

    API_HOST: str = os.getenv(
        "API_HOST",
        "0.0.0.0"
    )

    API_PORT: int = int(
        os.getenv(
            "API_PORT",
            "8000"
        )
    )

    APP_NAME: str = os.getenv(
        "APP_NAME",
        "Vedzovi Backend"
    )

    APP_VERSION: str = os.getenv(
        "APP_VERSION",
        "0.5.0-beta"
    )

    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000"
    )

    PRODUCTION_URL: str = os.getenv(
        "PRODUCTION_URL",
        "https://vedzovi.com"
    )

    WWW_PRODUCTION_URL: str = os.getenv(
        "WWW_PRODUCTION_URL",
        "https://www.vedzovi.com"
    )

    DATABASE_FOLDER: str = os.getenv(
        "DATABASE_FOLDER",
        "data"
    )

    DATABASE_NAME: str = os.getenv(
        "DATABASE_NAME",
        "agc.db"
    )

    UPLOAD_FOLDER: str = os.getenv(
        "UPLOAD_FOLDER",
        "storage/uploads"
    )

    OUTPUT_FOLDER: str = os.getenv(
        "OUTPUT_FOLDER",
        "outputs"
    )

    FRAME_FOLDER: str = os.getenv(
        "FRAME_FOLDER",
        "storage/frames"
    )

    THUMBNAIL_FOLDER: str = os.getenv(
        "THUMBNAIL_FOLDER",
        "storage/thumbnails"
    )

    HIGHLIGHT_FOLDER: str = os.getenv(
        "HIGHLIGHT_FOLDER",
        "storage/highlights"
    )

    PROGRESS_FILE: str = os.getenv(
        "PROGRESS_FILE",
        "storage/progress.json"
    )

    RESULTS_FOLDER: str = os.getenv(
        "RESULTS_FOLDER",
        "outputs/results"
    )

    JOBS_FOLDER: str = os.getenv(
        "JOBS_FOLDER",
        "storage/jobs"
    )

    # AGC-084: file-based maintenance sentinel. Presence of this file means
    # maintenance mode is ON. Toggled over SSH via scripts/maintenance.sh —
    # there is no admin auth surface or public toggle endpoint.
    MAINTENANCE_FLAG_PATH: str = os.getenv(
        "MAINTENANCE_FLAG_PATH",
        "storage/maintenance.flag"
    )

    MAX_UPLOAD_SIZE: int = int(
        os.getenv(
            "MAX_UPLOAD_SIZE",
            "524288000"
        )
    )

    MAX_UPLOAD_SIZE_MB: int = int(
        os.getenv(
            "MAX_UPLOAD_SIZE_MB",
            "500"
        )
    )

    # AGC-067.1: caps source video length at upload time so a legitimate
    # low-bitrate, long-duration upload cannot run past the AGC-067
    # FFMPEG_LONG_TIMEOUT_SECONDS during frame/audio extraction — file
    # size alone does not bound duration.
    MAX_VIDEO_DURATION_MINUTES: int = int(
        os.getenv(
            "MAX_VIDEO_DURATION_MINUTES",
            "30"
        )
    )

    MAX_CONCURRENT_JOBS_PER_USER: int = int(
        os.getenv(
            "MAX_CONCURRENT_JOBS_PER_USER",
            "2"
        )
    )

    MAX_CONCURRENT_JOBS: int = int(
        os.getenv(
            "MAX_CONCURRENT_JOBS",
            "4"
        )
    )

    TEMP_CLEANUP_HOURS: int = int(
        os.getenv(
            "TEMP_CLEANUP_HOURS",
            "24"
        )
    )

    # AGC-067: every ffmpeg/ffprobe subprocess call must bound its
    # runtime so a hung/malformed-input process cannot block a worker
    # indefinitely. Three tiers based on expected workload size.
    FFMPEG_QUICK_TIMEOUT_SECONDS: int = int(
        os.getenv(
            "FFMPEG_QUICK_TIMEOUT_SECONDS",
            "15"
        )
    )

    FFMPEG_SHORT_TIMEOUT_SECONDS: int = int(
        os.getenv(
            "FFMPEG_SHORT_TIMEOUT_SECONDS",
            "120"
        )
    )

    FFMPEG_LONG_TIMEOUT_SECONDS: int = int(
        os.getenv(
            "FFMPEG_LONG_TIMEOUT_SECONDS",
            "600"
        )
    )

    DUPLICATE_UPLOAD_WINDOW_MINUTES: int = int(
        os.getenv(
            "DUPLICATE_UPLOAD_WINDOW_MINUTES",
            "10"
        )
    )

    JWT_SECRET_KEY: str = _JWT_SECRET_KEY_ENV or secrets.token_hex(32)

    JWT_ALGORITHM: str = os.getenv(
        "JWT_ALGORITHM",
        "HS256"
    )

    JWT_EXPIRY_HOURS: int = int(
        os.getenv(
            "JWT_EXPIRY_HOURS",
            "24"
        )
    )

    ENVIRONMENT: str = os.getenv(
        "ENVIRONMENT",
        "development"
    )

    HTTPS_ENABLED: bool = (
        os.getenv(
            "HTTPS_ENABLED",
            "false"
        ).lower() == "true"
    )

    ADAPTIVE_THRESHOLD_ENABLED: bool = (
        os.getenv(
            "ADAPTIVE_THRESHOLD_ENABLED",
            "true"
        ).lower() == "true"
    )

    ADAPTIVE_THRESHOLD_PERCENTILE: int = int(
        os.getenv(
            "ADAPTIVE_THRESHOLD_PERCENTILE",
            "60"
        )
    )

    MIN_ADAPTIVE_THRESHOLD: float = float(
        os.getenv(
            "MIN_ADAPTIVE_THRESHOLD",
            "0.15"
        )
    )

    DEFAULT_HIGHLIGHT_THRESHOLD: float = float(
        os.getenv(
            "DEFAULT_HIGHLIGHT_THRESHOLD",
            "0.20"
        )
    )

    FINE_SCAN_WINDOW_SECONDS: int = int(
        os.getenv(
            "FINE_SCAN_WINDOW_SECONDS",
            "5"
        )
    )

    COARSE_TRIGGER_MULTIPLIER: float = float(
        os.getenv(
            "COARSE_TRIGGER_MULTIPLIER",
            "0.50"
        )
    )

    SYNERGY_ENABLED: bool = (
        os.getenv(
            "SYNERGY_ENABLED",
            "true"
        ).lower() == "true"
    )

    SYNERGY_SIGNAL_THRESHOLD: float = float(
        os.getenv(
            "SYNERGY_SIGNAL_THRESHOLD",
            "0.50"
        )
    )

    SYNERGY_INCREMENT: float = float(
        os.getenv(
            "SYNERGY_INCREMENT",
            "0.10"
        )
    )

    MAX_SYNERGY_MULTIPLIER: float = float(
        os.getenv(
            "MAX_SYNERGY_MULTIPLIER",
            "1.50"
        )
    )

    # VED-P1-007: Highlight Quality Gate — deterministic pre-acceptance
    # evidence check that runs on raw per-frame signals BEFORE category/
    # synergy amplification, so a candidate dominated by one signal
    # (typically scene_score) cannot cross the adaptive threshold purely
    # through multiplier stacking. See HighlightQualityGate.
    HIGHLIGHT_QUALITY_GATE_ENABLED: bool = (
        os.getenv(
            "HIGHLIGHT_QUALITY_GATE_ENABLED",
            "true"
        ).lower() == "true"
    )

    # ClipService scores are a softmax over ~20-30 profile prompts, not a
    # raw cosine similarity, so a confident match concentrates well above
    # the uniform baseline (~1/N). 0.30 sits comfortably below a confident
    # match (the production false positive measured 0.7317 here) while
    # still filtering frames with no real semantic relevance.
    HIGHLIGHT_MIN_CLIP_SCORE: float = float(
        os.getenv(
            "HIGHLIGHT_MIN_CLIP_SCORE",
            "0.30"
        )
    )

    # Meaningful-motion floor. Set below SYNERGY_SIGNAL_THRESHOLD (0.50,
    # the "strong signal" bar used for the synergy bonus) but above the
    # 0.2232 motion_score measured on the production false-positive frame,
    # so that exact pattern fails this bar deterministically.
    HIGHLIGHT_MIN_MOTION_SCORE: float = float(
        os.getenv(
            "HIGHLIGHT_MIN_MOTION_SCORE",
            "0.35"
        )
    )

    # Informational only: scene_score never counts toward the gate's
    # independent-evidence requirement (a high scene-change score alone —
    # e.g. a camera cut or HUD change — is not evidence of gameplay action).
    # It is still surfaced in HighlightQualityGate's quality_score for
    # explainability, at this floor as the "meaningful" bar.
    HIGHLIGHT_MIN_SCENE_SCORE: float = float(
        os.getenv(
            "HIGHLIGHT_MIN_SCENE_SCORE",
            "0.55"
        )
    )

    # Mirrors HIGHLIGHT_MIN_MOTION_SCORE. Never evaluated for silent
    # videos — AudioService already classifies those upstream via
    # AUDIO_SILENCE_THRESHOLD_DB, and the gate excludes audio entirely
    # (neither counted for nor against) rather than treating it as failure.
    HIGHLIGHT_MIN_AUDIO_SCORE: float = float(
        os.getenv(
            "HIGHLIGHT_MIN_AUDIO_SCORE",
            "0.35"
        )
    )

    # Number of independent action-evidence signals (motion, and audio
    # when the video is not silent) required to accept a candidate. 1 is
    # the least aggressive setting that still deterministically rejects
    # the production false positive (which had zero — motion below its
    # floor, audio excluded as silent), minimizing regression risk against
    # real gameplay already validated in production (e.g. SnowRunner).
    HIGHLIGHT_MIN_EVIDENCE_COUNT: int = int(
        os.getenv(
            "HIGHLIGHT_MIN_EVIDENCE_COUNT",
            "1"
        )
    )

    # AGC-082.2 — absolute noise-floor gate, in dBFS (decibels relative to
    # 16-bit PCM full scale). AudioService.build_audio_map() classifies a
    # decoded audio track as silent when its loudest sample is at or below
    # this level, BEFORE the existing peak/max_amplitude normalization runs.
    # Without this gate, any nonzero track — even pure encoder noise floor —
    # normalizes its single loudest instant to a score of 1.0, regardless of
    # how quiet that track actually is in absolute terms.
    #
    # -60 dBFS matches ffmpeg's own `silencedetect` filter default noise
    # threshold, a widely used convention for "no meaningful audio content."
    # Production evidence for this fix measured -76.3 dBFS max_volume on a
    # near-silent recording (comfortably below this gate), while genuine
    # quiet-but-meaningful gameplay audio (dialogue, ambience, UI sounds)
    # typically peaks well above -40 dBFS and is unaffected.
    #
    # This is a data-classification threshold, not a scoring weight/threshold
    # — it does not change SYNERGY_SIGNAL_THRESHOLD, category weights, or any
    # explainability reason threshold.
    AUDIO_SILENCE_THRESHOLD_DB: float = float(
        os.getenv(
            "AUDIO_SILENCE_THRESHOLD_DB",
            "-60.0"
        )
    )

    FREE_CREDITS: int = int(
        os.getenv(
            "FREE_CREDITS",
            "3"
        )
    )

    RAZORPAY_KEY_ID: str = os.getenv(
        "RAZORPAY_KEY_ID",
        ""
    )

    RAZORPAY_KEY_SECRET: str = os.getenv(
        "RAZORPAY_KEY_SECRET",
        ""
    )

    # REVENUE-004: separate from RAZORPAY_KEY_SECRET — this HMACs webhook
    # deliveries from Razorpay's servers and is generated independently
    # when the webhook URL is registered in the Razorpay dashboard.
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET",
        ""
    )

    PASSWORD_RESET_TOKEN_EXPIRY_MINUTES: int = int(
        os.getenv(
            "PASSWORD_RESET_TOKEN_EXPIRY_MINUTES",
            "30"
        )
    )

    PASSWORD_RESET_MAX_PER_HOUR: int = int(
        os.getenv(
            "PASSWORD_RESET_MAX_PER_HOUR",
            "3"
        )
    )

    PASSWORD_RESET_COOLDOWN_SECONDS: int = int(
        os.getenv(
            "PASSWORD_RESET_COOLDOWN_SECONDS",
            "60"
        )
    )

    PASSWORD_RESET_ATTEMPT_MAX_PER_IP: int = int(
        os.getenv(
            "PASSWORD_RESET_ATTEMPT_MAX_PER_IP",
            "10"
        )
    )

    PASSWORD_RESET_ATTEMPT_WINDOW_MINUTES: int = int(
        os.getenv(
            "PASSWORD_RESET_ATTEMPT_WINDOW_MINUTES",
            "15"
        )
    )

    # AGC-069: global rate limiter defaults. All window-based, per
    # RateLimitService (a generalization of the AGC-063.6 IP throttle).
    LOGIN_RATE_LIMIT_MAX_PER_MINUTE: int = int(
        os.getenv(
            "LOGIN_RATE_LIMIT_MAX_PER_MINUTE",
            "5"
        )
    )

    REGISTER_RATE_LIMIT_MAX_PER_MINUTE: int = int(
        os.getenv(
            "REGISTER_RATE_LIMIT_MAX_PER_MINUTE",
            "5"
        )
    )

    UPLOAD_RATE_LIMIT_MAX_PER_HOUR: int = int(
        os.getenv(
            "UPLOAD_RATE_LIMIT_MAX_PER_HOUR",
            "10"
        )
    )

    PIPELINE_START_RATE_LIMIT_MAX_PER_HOUR: int = int(
        os.getenv(
            "PIPELINE_START_RATE_LIMIT_MAX_PER_HOUR",
            "20"
        )
    )

    PAYMENT_VERIFY_RATE_LIMIT_MAX_PER_MINUTE: int = int(
        os.getenv(
            "PAYMENT_VERIFY_RATE_LIMIT_MAX_PER_MINUTE",
            "10"
        )
    )

    # AGC-071: rate limits for the two remaining unprotected public
    # endpoints, using the same generic RateLimitService as every other
    # limit above.
    PAYMENT_CREATE_ORDER_RATE_LIMIT_MAX_PER_MINUTE: int = int(
        os.getenv(
            "PAYMENT_CREATE_ORDER_RATE_LIMIT_MAX_PER_MINUTE",
            "10"
        )
    )

    VERIFY_EMAIL_RATE_LIMIT_MAX_PER_MINUTE: int = int(
        os.getenv(
            "VERIFY_EMAIL_RATE_LIMIT_MAX_PER_MINUTE",
            "10"
        )
    )

    EMAIL_FROM_ADDRESS: str = os.getenv(
        "EMAIL_FROM_ADDRESS",
        "noreply@vedzovi.com"
    )

    RESEND_API_KEY: str = os.getenv(
        "RESEND_API_KEY",
        ""
    )

    # VED-ANALYTICS-002: same PostHog project the frontend already uses
    # (see frontend/instrumentation-client.ts / NEXT_PUBLIC_POSTHOG_KEY).
    # PostHog project API keys are write-only/public by design — this is
    # not a new secret, just the same key reused server-side so job
    # completion can be tracked from the authoritative backend event
    # instead of depending on the browser tab staying open. Both empty by
    # default; AnalyticsService no-ops when either is unset, mirroring the
    # frontend's own `if (key && host)` guard.
    POSTHOG_API_KEY: str = os.getenv(
        "POSTHOG_API_KEY",
        ""
    )

    POSTHOG_HOST: str = os.getenv(
        "POSTHOG_HOST",
        ""
    )

    # AGC-070: email verification, reusing the same token/expiry pattern as
    # password reset. Links live longer (24h) since verification is not as
    # time-sensitive as a password reset.
    EMAIL_VERIFICATION_TOKEN_EXPIRY_MINUTES: int = int(
        os.getenv(
            "EMAIL_VERIFICATION_TOKEN_EXPIRY_MINUTES",
            "1440"
        )
    )

    RESEND_VERIFICATION_RATE_LIMIT_MAX_PER_HOUR: int = int(
        os.getenv(
            "RESEND_VERIFICATION_RATE_LIMIT_MAX_PER_HOUR",
            "5"
        )
    )

    # VED-OPS-001: internal Operations API (/api/v1/ops/*) — read-only,
    # aggregate-only surface consumed by Founder Pulse. Completely
    # independent from JWT_SECRET_KEY / customer auth.
    OPS_API_KEY: str = _OPS_API_KEY_ENV or ""

    OPS_CACHE_TTL_SECONDS: int = int(
        os.getenv(
            "OPS_CACHE_TTL_SECONDS",
            "15"
        )
    )

    # VED-P1-002: Production Monitoring. All thresholds below are additive —
    # they drive the new health engine only and never alter existing
    # HealthService/ObservabilityService/DiskSpaceService behavior or
    # thresholds (AGC-073's _DISK_WARNING_FREE_PERCENT, DiskSpaceService's
    # upload-guard MIN_FREE_PERCENT, etc. are untouched).
    HEALTH_SNAPSHOT_INTERVAL_MINUTES: int = int(
        os.getenv(
            "HEALTH_SNAPSHOT_INTERVAL_MINUTES",
            "5"
        )
    )

    # REVENUE-004: ReconciliationSchedulerService poll interval — same
    # daemon-thread pattern as HealthSchedulerService above.
    RECONCILIATION_INTERVAL_MINUTES: int = int(
        os.getenv(
            "RECONCILIATION_INTERVAL_MINUTES",
            "10"
        )
    )

    HEALTH_DISK_WARNING_PERCENT_USED: float = float(
        os.getenv(
            "HEALTH_DISK_WARNING_PERCENT_USED",
            "85.0"
        )
    )

    HEALTH_DISK_CRITICAL_PERCENT_USED: float = float(
        os.getenv(
            "HEALTH_DISK_CRITICAL_PERCENT_USED",
            "95.0"
        )
    )

    HEALTH_MEMORY_WARNING_PERCENT_USED: float = float(
        os.getenv(
            "HEALTH_MEMORY_WARNING_PERCENT_USED",
            "85.0"
        )
    )

    HEALTH_MEMORY_CRITICAL_PERCENT_USED: float = float(
        os.getenv(
            "HEALTH_MEMORY_CRITICAL_PERCENT_USED",
            "95.0"
        )
    )

    # Load average (1-minute), normalized by CPU core count. 1.0 == 100% of
    # available cores fully loaded.
    HEALTH_CPU_WARNING_LOAD_RATIO: float = float(
        os.getenv(
            "HEALTH_CPU_WARNING_LOAD_RATIO",
            "0.85"
        )
    )

    HEALTH_CPU_CRITICAL_LOAD_RATIO: float = float(
        os.getenv(
            "HEALTH_CPU_CRITICAL_LOAD_RATIO",
            "1.0"
        )
    )

    HEALTH_QUEUE_WARNING_MULTIPLIER: float = float(
        os.getenv(
            "HEALTH_QUEUE_WARNING_MULTIPLIER",
            "3.0"
        )
    )

    # Mirrors MissionControlService.FAILED_JOB_RATE_WARNING_THRESHOLD's
    # intent for the AI pipeline check, kept as an independently-tunable
    # value rather than importing that constant, since the two surfaces
    # (founder growth blockers vs. production health scoring) are allowed to
    # diverge over time without one accidentally moving the other.
    HEALTH_AI_PIPELINE_FAILURE_RATE_WARNING: float = float(
        os.getenv(
            "HEALTH_AI_PIPELINE_FAILURE_RATE_WARNING",
            "0.20"
        )
    )

    HEALTH_AI_PIPELINE_FAILURE_RATE_CRITICAL: float = float(
        os.getenv(
            "HEALTH_AI_PIPELINE_FAILURE_RATE_CRITICAL",
            "0.50"
        )
    )

    # Rolling window (minutes) used to compute payment/email failure rates
    # from monitoring_events.
    MONITORING_EVENT_WINDOW_MINUTES: int = int(
        os.getenv(
            "MONITORING_EVENT_WINDOW_MINUTES",
            "60"
        )
    )

    HEALTH_PAYMENT_FAILURE_WARNING_COUNT: int = int(
        os.getenv(
            "HEALTH_PAYMENT_FAILURE_WARNING_COUNT",
            "3"
        )
    )

    HEALTH_EMAIL_FAILURE_WARNING_COUNT: int = int(
        os.getenv(
            "HEALTH_EMAIL_FAILURE_WARNING_COUNT",
            "5"
        )
    )

    # scripts/backup.sh writes its outcome ("SUCCESS <ts>: <dest>" or
    # "FAILED <ts>: <reason>") to BACKUP_ROOT/last_backup_status. Read-only
    # from the backend — this app never triggers or writes backups itself.
    BACKUP_ROOT: str = os.getenv(
        "BACKUP_ROOT",
        "/opt/vedzovi-backups"
    )

    BACKUP_STALE_HOURS: int = int(
        os.getenv(
            "BACKUP_STALE_HOURS",
            "48"
        )
    )

    FRONTEND_HEALTH_CHECK_TIMEOUT_SECONDS: int = int(
        os.getenv(
            "FRONTEND_HEALTH_CHECK_TIMEOUT_SECONDS",
            "3"
        )
    )

    # Mirrors OPS_CACHE_TTL_SECONDS's role but for HealthEngineService.evaluate()
    # — bounds how often the (relatively expensive, Mission-Control-calling)
    # full evaluation actually recomputes, independent of how often the
    # admin dashboard or scheduler asks for it.
    HEALTH_ENGINE_CACHE_TTL_SECONDS: int = int(
        os.getenv(
            "HEALTH_ENGINE_CACHE_TTL_SECONDS",
            "15"
        )
    )

settings = Settings()
