# app/models/repository.py
from __future__ import annotations
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base
import uuid

if TYPE_CHECKING:
    from .user import User
    from .github import GitHubEvents
    from .webhooks import Webhook

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    full_name: Mapped[str] = mapped_column(unique=True)
    owner_login: Mapped[str]
    owner_type: Mapped[str]
    private: Mapped[bool]
    default_branch: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    language: Mapped[Optional[str]]
    topics: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    homepage: Mapped[Optional[str]]
    license: Mapped[Optional[dict]] = mapped_column(JSONB)
    stargazers_count: Mapped[int]
    forks_count: Mapped[int]
    created_at_gh: Mapped[Optional[datetime]]
    updated_at_gh: Mapped[Optional[datetime]]
    pushed_at_gh: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[List["GitHubEvents"]] = relationship(
        "GitHubEvents", back_populates="repository", cascade="all, delete-orphan"
    )
    user_links: Mapped[List["UserRepository"]] = relationship(
        "UserRepository", back_populates="repository", cascade="all, delete-orphan"
    )
    webhooks: Mapped[List["Webhook"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class UserRepository(Base):
    __tablename__ = "user_repository"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relationship: Mapped[str]

    user: Mapped["User"] = relationship("User", back_populates="repos")
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="user_links"
    )
