from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

import os
import shutil
import uuid
from pathlib import Path


router = APIRouter(
    prefix="/upload",
    tags=["Video Upload"]
)


MAX_FILE_SIZE = (
    500 * 1024 * 1024
)

ALLOWED_EXTENSIONS = {

    ".mp4",

    ".mov",

    ".mkv",

    ".avi"

}


@router.post("/")
async def upload_video(
    file: UploadFile = File(...)
):

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is missing."
        )

    extension = Path(
        file.filename
    ).suffix.lower()

    if (
        extension
        not in ALLOWED_EXTENSIONS
    ):

        raise HTTPException(

            status_code=400,

            detail=
            (
                "Only MP4, MOV, MKV and AVI files are allowed."
            )

        )

    file.file.seek(
        0,
        os.SEEK_END
    )

    file_size = (
        file.file.tell()
    )

    file.file.seek(0)

    if (
        file_size
        > MAX_FILE_SIZE
    ):

        raise HTTPException(

            status_code=400,

            detail=
            (
                "Maximum upload size is 500 MB."
            )

        )

    upload_dir = (
        "storage/uploads"
    )

    os.makedirs(
        upload_dir,
        exist_ok=True
    )

    original_name = (
        Path(file.filename)
        .stem
    )

    safe_name = (
        original_name
        .replace(" ", "_")
    )

    unique_filename = (
        f"{uuid.uuid4().hex[:8]}"
        f"_{safe_name}"
        f"{extension}"
    )

    file_path = os.path.join(
        upload_dir,
        unique_filename
    )

    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {error}"
        )

    return {

        "success": True,

        "message":
        "Video uploaded successfully 🎮",

        "filename":
        unique_filename,

        "original_filename":
        file.filename,

        "size_mb":
        round(
            file_size
            / 1024
            / 1024,
            2
        ),

        "location":
        file_path

    }