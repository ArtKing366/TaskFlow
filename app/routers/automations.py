from fastapi import APIRouter, Depends, status,Header
from sqlalchemy.orm import Session
from app.idempotency import execute_idempotent
from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.permissions import require_member, require_editor
from app.schemas import (
    AutomationCreate,
    AutomationUpdate,
    AutomationResponse,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/automations",
    tags=["Automations"],
)


@router.post(
    "/",
    response_model=AutomationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_automation_endpoint(
    workspace_id: int,
    automation_data: AutomationCreate,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return execute_idempotent(
        db=db,
        user_id=current_user.id,
        endpoint=f"POST:/workspaces/{workspace_id}/automations",
        key=idempotency_key,
        request_data=automation_data,
        operation=lambda: crud.create_automation(
            db,
            workspace_id,
            automation_data,
        ),
    )


@router.get(
    "/",
    response_model=list[AutomationResponse],
)
def list_automations(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_automations(
        db,
        workspace_id,
    )


@router.get(
    "/{automation_id}",
    response_model=AutomationResponse,
)
def get_automation_endpoint(
    workspace_id: int,
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_automation(
        db,
        automation_id,
        workspace_id,
    )


@router.patch(
    "/{automation_id}",
    response_model=AutomationResponse,
)
def update_automation_endpoint(
    workspace_id: int,
    automation_id: int,
    automation_data: AutomationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.update_automation(
        db,
        automation_id,
        workspace_id,
        automation_data,
    )


@router.delete(
    "/{automation_id}",
    response_model=dict[str, str],
)
def delete_automation_endpoint(
    workspace_id: int,
    automation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.delete_automation(
        db,
        automation_id,
        workspace_id,
    )
    
    
    
    
    
    
    
    
    
    