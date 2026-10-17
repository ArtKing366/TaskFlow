from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.permissions import require_member
from app.schemas import NotificationResponse


router = APIRouter(
    prefix="/workspaces/{workspace_id}/notifications",
    tags=["Notifications"],
)


@router.get(
    "/",
    response_model=list[NotificationResponse],
)
def list_notifications(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_user_notifications(
        db,
        workspace_id,
        current_user.id,
    )