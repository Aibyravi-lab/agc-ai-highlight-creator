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

    FREE_CREDITS: int = int(
        os.getenv(
            "FREE_CREDITS",
            "3"
        )
    )


settings = Settings()
