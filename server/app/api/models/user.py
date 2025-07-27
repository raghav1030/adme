from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base

if TYPE_CHECKING:
    from .github import GitHubEvents
    from .repository import UserRepository
    from .user import Organisation, UserOrganisation, UserOAuth
    from .webhooks import Webhook

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_name: Mapped[Optional[str]]
    avatar_url: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    oauth_records: Mapped[List["UserOAuth"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    repos: Mapped[List["UserRepository"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    orgs: Mapped[List["UserOrganisation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    events: Mapped[List["GitHubEvents"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    webhooks: Mapped[List["Webhook"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str]
    domain: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    members: Mapped[List["UserOrganisation"]] = relationship(
        back_populates="organisation", cascade="all, delete-orphan"
    )


class OAuthProvider(Base):
    __tablename__ = "oauth_providers"

    provider: Mapped[str] = mapped_column(primary_key=True)
    issuer_url: Mapped[str]

    user_oauth: Mapped[List["UserOAuth"]] = relationship(
        back_populates="provider_rel", cascade="all, delete-orphan"
    )


class UserOAuth(Base):
    __tablename__ = "user_oauth"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider: Mapped[str] = mapped_column(
        ForeignKey("oauth_providers.provider"), primary_key=True
    )
    provider_uid: Mapped[Optional[str]]
    access_token: Mapped[Optional[str]]
    refresh_token: Mapped[Optional[str]]
    scope: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    expires_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="oauth_records")
    provider_rel: Mapped["OAuthProvider"] = relationship(back_populates="user_oauth")


class UserOrganisation(Base):
    __tablename__ = "user_organisation"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str]

    user: Mapped["User"] = relationship(back_populates="orgs")
    organisation: Mapped["Organisation"] = relationship(back_populates="members")
