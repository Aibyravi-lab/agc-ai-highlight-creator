from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.services.database_service import DatabaseService

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


DatabaseService.initialize()


app = FastAPI(
    title="AGC Backend",
    version="0.1"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(analysis_router)
app.include_router(frame_router)
app.include_router(vision_router)
app.include_router(highlight_router)
app.include_router(pipeline_router)
app.include_router(clip_router)
app.include_router(editor_router)
app.include_router(history_router)

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


@app.get("/health")
def health():

    return {
        "status":
        "Backend Running Successfully"
    }


@app.get("/version")
def version():

    return {

        "project": "AGC",

        "version": "0.0.16",

        "status":
        "Thumbnail Generation Phase"

    }