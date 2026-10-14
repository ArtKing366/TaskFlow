from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, AuditLog
from app.permissions import require_member
from app.schemas import AuditLogResponse


router = APIRouter(
    prefix="/workspaces/{workspace_id}/audit-logs",
    tags=["Audit Logs"],
)


@router.get("/", response_model=list[AuditLogResponse])
def read_audit_logs(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return (
        db.query(AuditLog)
        .filter(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .all()
    )