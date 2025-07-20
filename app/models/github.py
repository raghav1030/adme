# app/models/github.py
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKeyConstraint, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .repository import Repository
    from .content import Summaries


class GitHubEvents(Base):
    __tablename__ = "github_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    occurred_at: Mapped[datetime] = mapped_column(primary_key=True)

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    repo_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    event_type: Mapped[str]
    event_id_gh: Mapped[int] = mapped_column(unique=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # relationships
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="events"
    )
    user: Mapped["User"] = relationship("User", back_populates="events")
    code_changes: Mapped[list["CodeChanges"]] = relationship(
        "CodeChanges", back_populates="event", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["Summaries"]] = relationship(
        "Summaries",
        back_populates="event",
        cascade="all, delete-orphan",  # ← orphan cleanup here
    )


class CodeChanges(Base):
    __tablename__ = "code_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    sha: Mapped[Optional[str]]
    patch: Mapped[Optional[str]]
    files_changed: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "occurred_at"],
            ["github_events.id", "github_events.occurred_at"],
            ondelete="CASCADE",
        ),
    )

    event: Mapped["GitHubEvents"] = relationship(
        "GitHubEvents", back_populates="code_changes"
    )
