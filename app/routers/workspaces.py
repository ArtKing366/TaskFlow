from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Membership, Role, User, Workspace
from app.schemas import WorkspaceCreate, WorkspaceResponse


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse)
def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = Workspace(
        name=workspace_data.name
    )

    db.add(workspace)
    db.flush()

    membership = Membership(
        user_id=current_user.id,
        workspace_id=workspace.id,
        role=Role.owner
    )

    db.add(membership)
    db.commit()
    db.refresh(workspace)

    return workspace