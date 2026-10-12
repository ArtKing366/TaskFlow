
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import (
    Project,
    Workspace,
    Task,
    TaskTag,
    User,
    TaskStatus,
)
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    TaskCreate,
    TaskUpdate,
    TaskPriority,
)
from app.permissions import is_workspace_member


def is_workspace_exist(db: Session, workspace_id: int):
    return (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .first()
    )

def get_projects(db: Session, workspace_id: int):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return (
        db.query(Project)
        .filter(Project.workspace_id == workspace_id)
        .all()
    )


def get_project(
    db: Session,
    project_id: int,
    workspace_id: int,
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project

def create_project(db: Session, project_data: ProjectCreate):
    workspace = is_workspace_exist(db, project_data.workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    c_project = Project(
        workspace_id=project_data.workspace_id,
        title=project_data.title,
        description=project_data.description,
    )

    db.add(c_project)
    db.commit()
    db.refresh(c_project)

    return c_project


def update_project(
    db: Session,
    project_id: int,
    workspace_id: int,
    project_data: ProjectUpdate,
):
    u_project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if u_project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    update_data = project_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(u_project, field, value)

    db.commit()
    db.refresh(u_project)

    return u_project


def delete_project(
    db: Session,
    project_id: int,
    workspace_id: int,
):
    d_project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if d_project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    task_ids = [
        task_id
        for (task_id,) in (
            db.query(Task.id)
            .filter(Task.project_id == project_id)
            .all()
        )
    ]

    if task_ids:
        db.query(TaskTag).filter(
            TaskTag.task_id.in_(task_ids)
        ).delete(synchronize_session=False)

        db.query(Task).filter(
            Task.project_id == project_id
        ).delete(synchronize_session=False)

    db.delete(d_project)
    db.commit()

    return {"detail": "Project deleted successfully"}
def get_tasks(
    db: Session,
    project_id: int,
    workspace_id: int,
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .all()
    )


def get_task(
    db: Session,
    task_id: int,
    workspace_id: int,
):
    task = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.id == task_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task


def create_task(
    db: Session,
    task_create: TaskCreate,
    workspace_id: int,
):
    project = (
        db.query(Project)
        .filter(
            Project.id == task_create.project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    if task_create.assignee_id is not None:
        assignee = (
            db.query(User)
            .filter(User.id == task_create.assignee_id)
            .first()
        )

        if assignee is None:
            raise HTTPException(
                status_code=404,
                detail="Assignee not found",
            )

        membership = is_workspace_member(
            assignee,
            workspace_id,
            db,
        )

        if membership is None:
            raise HTTPException(
                status_code=400,
                detail="Assignee is not a member of this workspace",
            )

    c_task = Task(
        project_id=task_create.project_id,
        title=task_create.title,
        description=task_create.description,
        status=task_create.status,
        priority=task_create.priority,
        deadline=task_create.deadline,
        assignee_id=task_create.assignee_id,
    )

    db.add(c_task)
    db.commit()
    db.refresh(c_task)

    return c_task


def update_task(
    db: Session,
    task_id: int,
    workspace_id: int,
    task_update: TaskUpdate,
):
    u_task = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.id == task_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if u_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    update_data = task_update.model_dump(exclude_unset=True)

    if (
        "assignee_id" in update_data
        and update_data["assignee_id"] is not None
    ):
        assignee = (
            db.query(User)
            .filter(User.id == update_data["assignee_id"])
            .first()
        )

        if assignee is None:
            raise HTTPException(
                status_code=404,
                detail="Assignee not found",
            )

        membership = is_workspace_member(
            assignee,
            workspace_id,
            db,
        )

        if membership is None:
            raise HTTPException(
                status_code=400,
                detail="Assignee is not a member of this workspace",
            )

    for field, value in update_data.items():
        setattr(u_task, field, value)

    db.commit()
    db.refresh(u_task)

    return u_task


def complete_task(
    db: Session,
    task_id: int,
    workspace_id: int,
):
    c_task = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.id == task_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if c_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    c_task.status = TaskStatus.done

    db.commit()
    db.refresh(c_task)

    return c_task


def assign_task(
    db: Session,
    task_id: int,
    assign_id: int,
    workspace_id: int,
):
    a_task = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.id == task_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if a_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    assignee = (
        db.query(User)
        .filter(User.id == assign_id)
        .first()
    )

    if assignee is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    membership = is_workspace_member(
        assignee,
        workspace_id,
        db,
    )

    if membership is None:
        raise HTTPException(
            status_code=400,
            detail="User is not a member of this workspace",
        )

    a_task.assignee_id = assignee.id

    db.commit()
    db.refresh(a_task)

    return a_task

def delete_task(
    db: Session,
    task_id: int,
    workspace_id: int,
):
    d_task = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.id == task_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if d_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    db.query(TaskTag).filter(
        TaskTag.task_id == task_id
    ).delete(synchronize_session=False)

    db.delete(d_task)
    db.commit()

    return {"detail": "Task deleted successfully"}


def filter_tasks(
    db: Session,
    project_id: int,
    workspace_id: int,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    query = db.query(Task).filter(
        Task.project_id == project_id
    )

    if status is not None:
        query = query.filter(Task.status == status)

    if priority is not None:
        query = query.filter(Task.priority == priority)

    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)

    if search is not None and search.strip():
        query = query.filter(
            Task.title.ilike(f"%{search.strip()}%")
        )

    return query.all()