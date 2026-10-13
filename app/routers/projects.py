from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import User, Role
from app.permissions import require_member
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse


router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects",
    tags=["Projects"],
)


def require_editor(
    current_user: User,
    workspace_id: int,
    db: Session,
):
    membership = require_member(current_user, workspace_id, db)

    if membership.role == Role.viewer:
        raise HTTPException(
            status_code=403,
            detail="Viewers cannot modify projects",
        )


@router.get("/", response_model=list[ProjectResponse])
def read_projects(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_projects(db, workspace_id)


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(
    workspace_id: int,
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    if project_data.workspace_id != workspace_id:
        raise HTTPException(
            status_code=400,
            detail="Workspace ID in the URL and request body must match",
        )

    return crud.create_project(db, project_data,current_user.id,)


@router.get("/{project_id}", response_model=ProjectResponse)
def read_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_project(db, project_id, workspace_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    workspace_id: int,
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.update_project(
        db,
        project_id,
        workspace_id,
        project_data,
        current_user.id,
    )


@router.delete("/{project_id}")
def delete_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.delete_project(db, project_id, workspace_id, current_user.id,)