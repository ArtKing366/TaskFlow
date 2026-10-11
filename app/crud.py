
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Project, Workspace


def is_workspace_exist(db: Session, workspace_id: int):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .first()
    )
    return workspace


def get_projects(db: Session, workspace_id: int):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    projects = (
        db.query(Project)
        .filter(Project.workspace_id == workspace_id)
        .all()
    )
    return projects


def get_project(
    db: Session,
    project_id: int,
    workspace_id: int,
):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project