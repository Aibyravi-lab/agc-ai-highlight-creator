from fastapi import APIRouter, UploadFile, File
import os
import shutil


router = APIRouter(
    prefix="/upload",
    tags=["Video Upload"]
)


@router.post("/")
async def upload_video(file: UploadFile = File(...)):
    os.makedirs("storage/uploads", exist_ok=True)
    # Create file path
    file_path = f"storage/uploads/{file.filename}"

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "Video uploaded successfully 🎮",
        "filename": file.filename,
        "location": file_path
    }