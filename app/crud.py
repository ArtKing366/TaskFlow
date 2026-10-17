
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.automation_engine import dispatch_event
from app.models import (Project,Workspace,Task,TaskTag,User,TaskStatus,AuditLog,   
    AuditLog,Automation,Notification)

from app.schemas import (ProjectCreate,ProjectUpdate,TaskCreate,TaskUpdate,TaskPriority,
    AutomationCreate,AutomationUpdate,)

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


def get_project(db: Session,project_id: int,workspace_id: int,):
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

def create_project(
    db: Session,
    project_data: ProjectCreate,
    user_id: int,
):
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
    db.flush()

    create_audit_log(
        db=db,
        workspace_id=c_project.workspace_id,
        user_id=user_id,
        action="project.created",
        entity_type="project",
        entity_id=c_project.id,
    )

    db.commit()
    db.refresh(c_project)

    return c_project


def update_project(
    db: Session,
    project_id: int,
    workspace_id: int,
    project_data: ProjectUpdate,
    user_id: int,
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

    db.flush()

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="project.updated",
        entity_type="project",
        entity_id=u_project.id,
    )

    db.commit()
    db.refresh(u_project)

    return u_project


def delete_project(
    db: Session,
    project_id: int,
    workspace_id: int,
    user_id: int,
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

    db.query(TaskTag).filter(
        TaskTag.task_id.in_(
            db.query(Task.id).filter(
                Task.project_id == project_id
            )
        )
    ).delete(synchronize_session=False)

    db.query(Task).filter(
        Task.project_id == project_id
    ).delete(synchronize_session=False)

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="project.deleted",
        entity_type="project",
        entity_id=d_project.id,
    )

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
    user_id: int,
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
    db.flush()

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="task.created",
        entity_type="task",
        entity_id=c_task.id,
    )

    db.commit()
    db.refresh(c_task)

    return c_task


def update_task(
    db: Session,
    task_id: int,
    workspace_id: int,
    task_update: TaskUpdate,
    user_id: int,
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

    db.flush()

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="task.updated",
        entity_type="task",
        entity_id=u_task.id,
    )

    db.commit()
    db.refresh(u_task)

    return u_task

def complete_task(db: Session,task_id: int,
    workspace_id: int,user_id: int,):
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

    try:
        if c_task.status != TaskStatus.done:
            c_task.status = TaskStatus.done

            db.flush()

            create_audit_log(
                db=db,
                workspace_id=workspace_id,
                user_id=user_id,
                action="task.completed",
                entity_type="task",
                entity_id=c_task.id,
            )

            dispatch_event(
                db=db,
                workspace_id=workspace_id,
                event_name="task.completed",
                task=c_task,
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(c_task)

    return c_task


def assign_task(
    db: Session,
    task_id: int,
    assign_id: int,
    workspace_id: int,
    user_id: int,
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

    if a_task.assignee_id != assignee.id:
        a_task.assignee_id = assignee.id

        db.flush()

        create_audit_log(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            action="task.assigned",
            entity_type="task",
            entity_id=a_task.id,
        )

    db.commit()
    db.refresh(a_task)

    return a_task
def delete_task(
    db: Session,
    task_id: int,
    workspace_id: int,
    user_id: int,
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

    create_audit_log(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        action="task.deleted",
        entity_type="task",
        entity_id=d_task.id,
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

def create_audit_log(db: Session,workspace_id: int,user_id: int,action: str,entity_type: str,
    entity_id: int,) -> AuditLog:
    
    audit_log = AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    db.add(audit_log)
    db.flush()

    return audit_log

def create_automation(
    db: Session,
    workspace_id: int,
    automation_data: AutomationCreate,
):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    data = automation_data.model_dump(mode="json")

    c_automation = Automation(
        workspace_id=workspace_id,
        **data,
    )

    db.add(c_automation)
    db.commit()
    db.refresh(c_automation)

    return c_automation


def get_automations(
    db: Session,
    workspace_id: int,
):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return (
        db.query(Automation)
        .filter(Automation.workspace_id == workspace_id)
        .order_by(
            Automation.created_at.desc(),
            Automation.id.desc(),
        )
        .all()
    )


def get_automation(
    db: Session,
    automation_id: int,
    workspace_id: int,
):
    automation = (
        db.query(Automation)
        .filter(
            Automation.id == automation_id,
            Automation.workspace_id == workspace_id,
        )
        .first()
    )

    if automation is None:
        raise HTTPException(
            status_code=404,
            detail="Automation not found",
        )

    return automation

def update_automation(
    db: Session,
    automation_id: int,
    workspace_id: int,
    automation_data: AutomationUpdate,
):
    u_automation = (
        db.query(Automation)
        .filter(
            Automation.id == automation_id,
            Automation.workspace_id == workspace_id,
        )
        .first()
    )

    if u_automation is None:
        raise HTTPException(
            status_code=404,
            detail="Automation not found",
        )

    update_data = automation_data.model_dump(
        mode="json",
        exclude_unset=True,
    )

    required_fields = {
        "name",
        "trigger",
        "action",
        "is_active",
    }

    for field in required_fields:
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    for field, value in update_data.items():
        setattr(u_automation, field, value)

    db.commit()
    db.refresh(u_automation)

    return u_automation

def delete_automation(
    db: Session,
    automation_id: int,
    workspace_id: int,
):
    d_automation = (
        db.query(Automation)
        .filter(
            Automation.id == automation_id,
            Automation.workspace_id == workspace_id,
        )
        .first()
    )

    if d_automation is None:
        raise HTTPException(
            status_code=404,
            detail="Automation not found",
        )

    db.delete(d_automation)
    db.commit()

    return {
        "detail": "Automation deleted successfully"
    }

def get_user_notifications(
    db: Session,
    workspace_id: int,
    user_id: int,
):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return (
        db.query(Notification)
        .filter(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user_id,
        )
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .all()
    )



