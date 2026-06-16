from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.upload import router as upload_router
from app.routers.analysis import router as analysis_router
from app.routers.frame import router as frame_router


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

@app.get("/")
def home():
    return {
        "message": "Welcome to AGC AI Gaming Highlight Creator 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "Backend Running Successfully"
    }