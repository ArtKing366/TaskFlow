from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import Header
from app.idempotency import execute_idempotent
from fastapi.encoders import jsonable_encoder

from app.redis_cache import get_cached_json, set_cached_json

from app import crud
from app.auth import get_current_user
from app.database import get_db
from app.models import User, Role, TaskStatus
from app.permissions import require_member
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskPriority,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}",
    tags=["Tasks"],
)


def require_editor(
    current_user: User,
    workspace_id: int,
    db: Session,
):
    membership = require_member(current_user, workspace_id, db)

    if membership.role == Role.viewer:
        raise HTTPException(
            status_code=403,
            detail="Viewers cannot modify tasks",
        )


@router.get(
    "/projects/{project_id}/tasks",
    response_model=list[TaskResponse],
)
def read_tasks(
    workspace_id: int,
    project_id: int,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    require_member(current_user, workspace_id, db)

    cache_key = (
        f"taskflow:cache:tasks:workspace:{workspace_id}:"
        f"project:{project_id}:"
        f"status:{status.value if status else 'all'}:"
        f"priority:{priority.value if priority else 'all'}:"
        f"assignee:{assignee_id if assignee_id is not None else 'all'}:"
        f"search:{search.strip() if search and search.strip() else ''}"
    )

    cached_tasks = get_cached_json(cache_key)

    if cached_tasks is not None:
        return cached_tasks

    tasks = crud.filter_tasks(
        db=db,
        project_id=project_id,
        workspace_id=workspace_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
    )

    tasks_data = jsonable_encoder(tasks)

    set_cached_json(
        cache_key,
        tasks_data,
        ttl=300,
    )

    return tasks_data



@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=201,
)
def create_task(
    workspace_id: int,
    project_id: int,
    task_data: TaskCreate,
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

    if task_data.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Project ID in the URL and request body must match",
        )

    return execute_idempotent(
        db=db,
        user_id=current_user.id,
        endpoint=(
            f"POST:/workspaces/{workspace_id}"
            f"/projects/{project_id}/tasks"
        ),
        key=idempotency_key,
        request_data=task_data,
        operation=lambda: crud.create_task(
            db,
            task_data,
            workspace_id,
            current_user.id,
        ),
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
def read_task(
    workspace_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_member(current_user, workspace_id, db)

    return crud.get_task(db, task_id, workspace_id)


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    workspace_id: int,
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.update_task(
        db,
        task_id,
        workspace_id,
        task_data,
        current_user.id,
    )


@router.patch(
    "/tasks/{task_id}/complete",
    response_model=TaskResponse,
)
def complete_task(
    workspace_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.complete_task(
        db,
        task_id,
        workspace_id,
        current_user.id,
    )


@router.patch(
    "/tasks/{task_id}/assign/{assign_id}",
    response_model=TaskResponse,
)
def assign_task(
    workspace_id: int,
    task_id: int,
    assign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.assign_task(
        db,
        task_id,
        assign_id,
        workspace_id,
        current_user.id,    
    )


@router.delete("/tasks/{task_id}")
def delete_task(
    workspace_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_editor(current_user, workspace_id, db)

    return crud.delete_task(
        db,
        task_id,
        workspace_id,
        current_user.id,
    )