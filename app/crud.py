from sqlalchemy.orm import Session
from app.models import Project


def get_projects(db: Session, workspace_id: int):
    projects = (
        db.query(Project).filter(Project.workspace_id == workspace_id).all()
    )
    return projects