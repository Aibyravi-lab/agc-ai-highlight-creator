from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

import os
import shutil


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

    ".mkv"

}


@router.post("/")
async def upload_video(
    file: UploadFile = File(...)
):

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if (
        extension
        not in ALLOWED_EXTENSIONS
    ):

        raise HTTPException(

            status_code=400,

            detail=
            (
                "Only MP4, MOV and MKV "
                "files are allowed."
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
                "Maximum upload size "
                "is 500 MB."
            )

        )

    os.makedirs(
        "storage/uploads",
        exist_ok=True
    )

    file_path = (
        f"storage/uploads/"
        f"{file.filename}"
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    return {

        "success": True,

        "message":
        "Video uploaded successfully 🎮",

        "filename":
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