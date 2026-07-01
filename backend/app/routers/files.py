from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import get_current_user
from app.services.job_service import JobService


router = APIRouter(tags=["File Downloads"])

ALLOWED_ROOTS = {"storage", "outputs"}


@router.get("/files/{file_path:path}")
def download_file(
    file_path: str,
    current_user: dict = Depends(get_current_user)
):

    normalized = file_path.replace("\\", "/")

    # Reject path traversal in any component
    components = normalized.split("/")
    if ".." in components or "" in components[1:]:
        raise HTTPException(
            status_code=400,
            detail="Invalid path"
        )

    # Restrict to known output roots
    root = components[0] if components else ""
    if root not in ALLOWED_ROOTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid path"
        )

    # Verify ownership: the path must appear in one of this
    # user's job results.
    if not JobService.user_owns_file(
        current_user["id"],
        normalized
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    disk_path = Path(normalized)

    if not disk_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(str(disk_path))
