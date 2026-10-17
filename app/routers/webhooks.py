from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.permissions import require_member, require_editor
from app.schemas import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/webhooks",
    tags=["Webhooks"],
)


@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_webhook_endpoint(
    workspace_id: int,
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.create_webhook(
        db,
        workspace_id,
        webhook_data,
    )


@router.get(
    "/",
    response_model=list[WebhookResponse],
)
def list_webhooks(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_webhooks(
        db,
        workspace_id,
    )


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
)
def get_webhook_endpoint(
    workspace_id: int,
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_webhook(
        db,
        webhook_id,
        workspace_id,
    )


@router.patch(
    "/{webhook_id}",
    response_model=WebhookResponse,
)
def update_webhook_endpoint(
    workspace_id: int,
    webhook_id: int,
    webhook_data: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.update_webhook(
        db,
        webhook_id,
        workspace_id,
        webhook_data,
    )


@router.delete(
    "/{webhook_id}",
    response_model=dict[str, str],
)
def delete_webhook_endpoint(
    workspace_id: int,
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.delete_webhook(
        db,
        webhook_id,
        workspace_id,
    )