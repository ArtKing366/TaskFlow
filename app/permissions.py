from app.models import User, Membership
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends


def is_workspace_member(user: User,workspace_id: int,db: Session):
    return (
            db.query(Membership)
            .filter(
                Membership.user_id == user.id,
                Membership.workspace_id == workspace_id
            )
            .first()
        )
    





