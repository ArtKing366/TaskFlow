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


@router.post("/", response_model=list[AutomationCreate])
def create_automations_endpoint():
    pass


@router.get("/", response_model=list[AutomationResponse])
def list_automations():
    pass


@router.get("/{automation_id}", response_model=list[AutomationResponse])
def get_automation():
    pass


@router.post("/{automation_id}", response_model=list[AutomationUpdate])
def change_automation():
    pass





