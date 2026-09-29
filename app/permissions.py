from app.models import User, Membership,Role
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends, HTTPException


def is_workspace_member(user: User,workspace_id: int,db: Session):
    return (
            db.query(Membership)
            .filter(
                Membership.user_id == user.id,
                Membership.workspace_id == workspace_id
            )
            .first()
        )
    
def require_member(user:User, workspace_id:int, db:Session):
    membership = is_workspace_member(user,workspace_id,db)
    if membership is None:
        return HTTPException(
            status_code=403,
            detail="Not a member workspce"
        )

    return membership


def require_admin(user:User, workspace_id:int, db:Session):
    membership = is_workspace_member(user,workspace_id,db)
    if membership.role not in (Role.admin, Role.owner):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return membership


def require_owner(
    user: User,
    workspace_id: int,
    db: Session
) -> Membership:
    membership = require_member(user, workspace_id, db)

    if membership.role != Role.owner:
        raise HTTPException(
            status_code=403,
            detail="Owner access required"
        )

    return membership







