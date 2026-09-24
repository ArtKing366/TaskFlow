from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "memberships"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "workspace_id",
            name="uq_membership_user_workspace"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    role: Mapped[Role] = mapped_column(default=Role.member)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    user: Mapped["User"] = relationship(
        back_populates="memberships"
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="memberships"
    )