
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Project, Workspace,Task,User,TaskStatus
from app.schemas import ProjectCreate,ProjectUpdate,TaskCreate,TaskUpdate

from app.permissions import is_workspace_member

def is_workspace_exist(db: Session, workspace_id: int):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .first()
    )
    return workspace



def get_projects(db: Session, workspace_id: int):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    projects = (
        db.query(Project)
        .filter(Project.workspace_id == workspace_id)
        .all()
    )
    return projects


def get_project(
    db: Session,
    project_id: int,
    workspace_id: int,
):
    workspace = is_workspace_exist(db, workspace_id)

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

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

def create_project(db:Session, project_data:ProjectCreate):
    c_project = Project(
        workspace_id = project_data.workspace_id,
        title = project_data.title,
        description = project_data.description
    )
    
    db.add(c_project)
    db.commit()
    db.refresh(c_project)
    
    return c_project


def update_project(db:Session,project_id: int, project_data:ProjectUpdate):
    u_project = (
        db.query(Project)
        .filter(Project.id == project_id)
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

def delete_project(db:Session,project_id: int):
    d_project = (db.query(Project).filter(
        Project.id == project_id
    ).first())
    
    if d_project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )
    
    db.delete(d_project)
    db.commit()
    


def get_tasks(db: Session, project_id: int, workspace_id: int):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.workspace_id == workspace_id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return tasks

def get_task(db: Session, task_id: int, workspace_id: int):
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
        raise HTTPException(status_code=404, detail="Task not found")

    return task


def create_task(db: Session, task_create: TaskCreate):
    project = (
    db.query(Project)
    .filter(Project.id == task_create.project_id)
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
        project.workspace_id,
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


def update_task(db:Session,task_id: int, task_update: TaskUpdate):
    u_task = (
        db.query(Task).filter(
            Task.id == task_id
        ).first()
    )
    
    if u_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task was not found"
        )
        
    update_data = task_update.model_dump(exclude_unset=True)
    for field,value in update_data.items():
        setattr(u_task,field,value)
    
    db.commit()
    db.refresh(u_task)
    return u_task
    

def complete_task(db:Session, task_id:int ):
    c_task = (
        db.query(Task).filter(
            Task.id == task_id
        ).first()
    )
    
    if c_task is None:
        raise HTTPException(
            status_code=404,
            detail = "Task was not found"
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

def delete_task(db: Session, task_id: int):
    d_task = db.query(Task).filter(Task.id == task_id).first()

    if d_task is None:
        raise HTTPException(
            status_code=404,
            detail="Task was not found",
        )

    db.delete(d_task)
    db.commit()

    return {"detail": "Task deleted successfully"}
