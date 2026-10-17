from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

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


@router.post("/",response_model=AutomationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_automation_endpoint(
    workspace_id: int,
    automation_data: AutomationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.create_automation(
        db,
        workspace_id,
        automation_data,
    )



@router.get("/",response_model=list[AutomationResponse],)
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


@router.get("/{automation_id}", response_model=list[AutomationResponse])
def get_automation():
    pass


@router.post("/{automation_id}", response_model=list[AutomationUpdate])
def change_automation():
    pass





