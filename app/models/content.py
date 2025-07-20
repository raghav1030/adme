from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, Text, ForeignKeyConstraint, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base


class Summaries(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    summary_text: Mapped[str]
    tech_stack: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    embedding: Mapped[Optional[bytes]]  # or vector if you use the extension
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "occurred_at"],
            ["github_events.id", "github_events.occurred_at"],
            ondelete="CASCADE",
        ),
    )

    event: Mapped["GitHubEvents"] = relationship(
        back_populates="summaries",
    )


class Posts(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    repo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("repositories.id"))
    event_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    content_md: Mapped[str]
    target: Mapped[str]  # 'twitter'|'linkedin'|'journal'|'resume'
    status: Mapped[str] = mapped_column(server_default=text("'draft'"))
    context_hash: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    published_at: Mapped[Optional[datetime]]


class ResumeBullets(Base):
    __tablename__ = "resume_bullets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    repo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("repositories.id"))
    event_ids: Mapped[List[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    bullet_latex: Mapped[str]
    keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PostTemplates(Base):
    __tablename__ = "post_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    target: Mapped[str]  # enum values handled at app layer
    name: Mapped[Optional[str]]
    prompt: Mapped[str]
    is_default: Mapped[bool] = mapped_column(server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
