import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from dotenv import load_dotenv

from app.config.config import settings

from app.services.database_service import DatabaseService
from app.services.ffmpeg_service import FFmpegService
from app.services.logger_service import LoggerService

from app.routers.upload import router as upload_router
from app.routers.analysis import router as analysis_router
from app.routers.frame import router as frame_router
from app.routers.vision import router as vision_router
from app.routers.highlight import router as highlight_router
from app.routers.pipeline import router as pipeline_router
from app.routers.clip import router as clip_router
from app.routers.editor import router as editor_router
from app.routers.history import (
    router as history_router
)
from app.routers.auth import router as auth_router
from app.routers.files import router as files_router
from app.routers.projects import router as projects_router
from app.routers.observability import router as observability_router

load_dotenv()

print(
    "🚀 AGC Startup Validation"
)

DatabaseService.initialize()

FFmpegService.validate()

LoggerService.initialize()

LoggerService.info(
    "AGC Startup Validation Passed"
)

if (
    settings.ENVIRONMENT == "production"
    and not settings.HTTPS_ENABLED
):
    print(
        "⚠️  WARNING: ENVIRONMENT=production but HTTPS_ENABLED is not set."
    )
    print(
        "⚠️  Set HTTPS_ENABLED=true in .env and configure nginx TLS before public release."
    )

print(
    "✅ Startup Validation Completed"
)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    if settings.HTTPS_ENABLED:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next
) -> Response:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://45.94.209.92",
        settings.FRONTEND_URL,
        settings.PRODUCTION_URL,
        settings.WWW_PRODUCTION_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(observability_router)
app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(frame_router)
app.include_router(vision_router)
app.include_router(highlight_router)
app.include_router(pipeline_router)
app.include_router(clip_router)
app.include_router(editor_router)
app.include_router(history_router)
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(projects_router)

app.mount(
    "/storage",
    StaticFiles(directory="storage"),
    name="storage"
)

app.mount(
    "/outputs",
    StaticFiles(directory="outputs"),
    name="outputs"
)


@app.get("/")
def home():

    return {
        "message":
        "Welcome to AGC AI Gaming Highlight Creator 🚀"
    }


@app.get("/version")
def version():

    return {
        "project": "AGC",
        "version": settings.APP_VERSION,
        "status": "Production Readiness Phase"
    }
