import os
import secrets

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


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
        "AGC Backend"
    )

    APP_VERSION: str = os.getenv(
        "APP_VERSION",
        "0.0.17"
    )

    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000"
    )

    PRODUCTION_URL: str = os.getenv(
        "PRODUCTION_URL",
        "https://highlightai.in"
    )

    WWW_PRODUCTION_URL: str = os.getenv(
        "WWW_PRODUCTION_URL",
        "https://www.highlightai.in"
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

    MAX_UPLOAD_SIZE: int = int(
        os.getenv(
            "MAX_UPLOAD_SIZE",
            "524288000"
        )
    )

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        secrets.token_hex(32)
    )

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


settings = Settings()
