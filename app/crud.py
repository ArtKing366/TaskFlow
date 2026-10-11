from sqlalchemy.orm import Session
from app.models import Project


def get_projects(db: Session, workspace_id: int):
    projects = (
        db.query(Project).filter(Project.workspace_id == workspace_id).all()
    )
    return projects


def get_project(db:Session, project_id:int, workspace_id:int):
    project = (
        db.query(Project).filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id
        ).first
    )
    return project









