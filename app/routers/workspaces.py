from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Membership, Role, User, Workspace
from app.permissions import is_workspace_member
from app.schemas import WorkspaceCreate, WorkspaceResponse
from fastapi import Depends, HTTPException




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


@router.get("")
def get_workspace(current_user:User = Depends(get_current_user), db:Session = Depends(get_db)):
    worksapce = (
        db.query(Workspace)
        .join(Membership)
        .filter(Membership.user_id == current_user.id)
        .all()
        
    )
    
    return worksapce

@router.get("/workspace_id", response_model=WorkspaceResponse)
def get_workspace(workspace_id:int, current_user:User = Depends(get_current_user), db:Session = Depends(get_db)):
    membership = is_workspace_member(
        current_user, workspace_id, db
    )
    
    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="Not a workspace member"
        )

    workspace = db.get(Workspace, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found"
        )

    return workspace