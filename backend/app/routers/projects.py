from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.services.project_service import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)


@router.get("")
def list_projects(
    current_user: dict = Depends(get_current_user)
):

    projects = ProjectService.get_projects(
        user_id=current_user["id"]
    )

    return {
        "success": True,
        "count": len(projects),
        "data": projects
    }


@router.get("/{project_id}")
def get_project(
    project_id: int,
    current_user: dict = Depends(get_current_user)
):

    project = ProjectService.get_project(
        user_id=current_user["id"],
        project_id=project_id
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {
        "success": True,
        "data": project
    }


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: dict = Depends(get_current_user)
):

    deleted = ProjectService.delete_project(
        user_id=current_user["id"],
        project_id=project_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {
        "success": True,
        "message": "Project deleted"
    }
