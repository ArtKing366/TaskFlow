from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Role, TaskPriority, TaskStatus


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime

class WorkspaceBase(BaseModel):
    name: str


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = None


class WorkspaceResponse(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class MembershipBase(BaseModel):
    user_id: int
    workspace_id: int
    role: Role


class MembershipCreate(MembershipBase):
    pass


class MembershipUpdate(BaseModel):
    role: Role | None = None


class MembershipResponse(MembershipBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProjectBase(BaseModel):
    title: str
    description: str


class ProjectCreate(ProjectBase):
    workspace_id: int


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    created_at: datetime
    updated_at: datetime

class TaskBase(BaseModel):
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority


class TaskCreate(TaskBase):
    project_id: int
    deadline: datetime | None = None
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    deadline: datetime | None = None
    assignee_id: int | None = None


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    deadline: datetime | None
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    workspace_id: int


class TagUpdate(BaseModel):
    name: str | None = None


class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
class TaskTagBase(BaseModel):
    task_id: int
    tag_id: int


class TaskTagCreate(TaskTagBase):
    pass


class TaskTagResponse(TaskTagBase):
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int | None = None