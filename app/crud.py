
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Project, Workspace,Task
from app.schemas import ProjectCreate,ProjectUpdate

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

def create_project(db:Session, project_data:ProjectCreate):
    c_project = Project(
        workspace_id = project_data.workspace_id,
        title = project_data.title,
        description = project_data.description
    )
    
    db.add(c_project)
    db.commit()
    db.refresh(c_project)
    
    return c_project


def update_project(db:Session,project_id: int, project_data:ProjectUpdate):
    u_project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if u_project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    update_data = project_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(u_project, field, value)

    db.commit()
    db.refresh(u_project)

    return u_project

def delete_project(db:Session,project_id: int):
    d_project = (db.query(Project).filter(
        Project.id == project_id
    ).first())
    
    if d_project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )
    
    db.delete(d_project)
    db.commit()
    


def get_tasks(db: Session, project_id: int, workspace_id: int):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return tasks

def get_task():
    
    pass

