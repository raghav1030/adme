from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field, validator
from app.api.core.config import settings
from app.api.core.database import AsyncSession, get_db_session
from app.api.models import User, UserOAuth, OAuthProvider
from app.api.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    encrypt_token,
)
from app.api.dependencies.auth import get_current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
import httpx
from datetime import timedelta
import uuid
from typing import List, Optional
import datetime

router = APIRouter()

# --- Pydantic Models ---


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class LoginSuccessResponse(BaseModel):
    message: str
    user: UserProfileResponse
    tokens: TokenResponse


class UserSignup(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=8)  # Enforce minimum password length
    retype_password: str

    @validator("retype_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# --- Helper Functions ---


async def ensure_github_provider(db: AsyncSession):
    stmt = select(OAuthProvider).where(OAuthProvider.provider == "github")
    result = await db.execute(stmt)
    provider = result.scalar_one_or_none()
    if not provider:
        provider = OAuthProvider(provider="github", issuer_url="https://github.com")
        db.add(provider)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()


# --- Authentication Endpoints ---


@router.post(
    "/signup", response_model=LoginSuccessResponse, status_code=status.HTTP_201_CREATED
)
async def signup_email_password(
    user_data: UserSignup, db: AsyncSession = Depends(get_db_session)
):
    """
    Registers a new user with email and password, and returns JWT tokens.
    """
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    hashed_password = hash_password(user_data.password)

    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        avatar_url=None,
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during registration. Email might already exist.",
        )

    access_token = create_access_token(data={"user_id": str(new_user.id)})
    refresh_token = create_refresh_token(data={"user_id": str(new_user.id)})

    return LoginSuccessResponse(
        message="User registered and logged in successfully.",
        user=UserProfileResponse.model_validate(new_user),
        tokens=TokenResponse(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/login/email-password", response_model=LoginSuccessResponse)
async def login_email_password(
    user_login: UserLogin, db: AsyncSession = Depends(get_db_session)
):
    """
    Authenticates a user with email and password, and returns JWT access and refresh tokens.
    """
    stmt = select(User).where(User.email == user_login.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if (
        not user
        or not user.hashed_password
        or not verify_password(user_login.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"user_id": str(user.id)})
    refresh_token = create_refresh_token(data={"user_id": str(user.id)})

    return LoginSuccessResponse(
        message="Logged in successfully.",
        user=UserProfileResponse.model_validate(user),
        tokens=TokenResponse(access_token=access_token, refresh_token=refresh_token),
    )


@router.get("/oauth/github")
async def login_github():
    """
    Initiates the GitHub OAuth login flow by redirecting the user.
    """
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
        f"scope=user,repo&"
        f"state={settings.APP_SECRET_KEY}"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/oauth/github/callback", response_model=LoginSuccessResponse)
async def github_callback(
    request: Request, code: str, state: str, db: AsyncSession = Depends(get_db_session)
):
    """
    Handles the callback from GitHub OAuth.
    Authenticates the user and issues JWT tokens.
    """
    if state != settings.APP_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter"
        )

    await ensure_github_provider(db)

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from GitHub: {token_response.text}",
            )

        token_data = token_response.json()
        github_access_token = token_data.get("access_token")
        github_refresh_token = token_data.get("refresh_token")
        scope = (
            token_data.get("scope", "").split(",") if token_data.get("scope") else []
        )
        expires_at = None  # GitHub's user access tokens often don't have a strict expiry or it's very long

        if not github_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received from GitHub",
            )

        # Fetch user info from GitHub
        user_info_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_access_token}"},
        )

        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info from GitHub: {user_info_response.text}",
            )

        user_data = user_info_response.json()
        github_user_id = str(user_data.get("id"))
        email = user_data.get("email")
        full_name = user_data.get("name")
        avatar_url = user_data.get("avatar_url")

        # If email is private on GitHub, fetch from user emails endpoint
        if not email:
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {github_access_token}"},
            )
            if emails_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get user emails from GitHub: {emails_response.text}",
                )
            emails = emails_response.json()
            primary_email = next((e["email"] for e in emails if e.get("primary")), None)
            email = primary_email or emails[0]["email"] if emails else None

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No primary email found for GitHub user.",
            )

        # Find or Create User in our DB
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # New user, create User record
            user = User(
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
                hashed_password=None,  # No password for OAuth users
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            # Existing user, update profile if needed
            user.full_name = full_name
            user.avatar_url = avatar_url
            user.updated_at = func.now()
            await db.commit()

        # Store/Update OAuth credentials
        encrypted_github_access_token = encrypt_token(github_access_token)
        encrypted_github_refresh_token = (
            encrypt_token(github_refresh_token) if github_refresh_token else None
        )
        stmt = select(UserOAuth).where(
            UserOAuth.user_id == user.id, UserOAuth.provider == "github"
        )
        result = await db.execute(stmt)
        user_oauth = result.scalar_one_or_none()

        if not user_oauth:
            user_oauth = UserOAuth(
                user_id=user.id,
                provider="github",
                provider_uid=github_user_id,
                access_token=encrypted_github_access_token,
                refresh_token=encrypted_github_refresh_token,
                scope=scope,
                expires_at=expires_at,
            )
            db.add(user_oauth)
        else:
            user_oauth.provider_uid = github_user_id
            user_oauth.access_token = encrypted_github_access_token
            user_oauth.refresh_token = encrypted_github_refresh_token
            user_oauth.scope = scope
            user_oauth.expires_at = expires_at
            user_oauth.created_at = (
                func.now()
            )  # Update created_at on re-auth for simplicity

        await db.commit()

        # Issue our application's JWT tokens
        app_access_token = create_access_token(data={"user_id": str(user.id)})
        app_refresh_token = create_refresh_token(data={"user_id": str(user.id)})

        return LoginSuccessResponse(
            message="GitHub authentication successful.",
            user=UserProfileResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=app_access_token, refresh_token=app_refresh_token
            ),
        )


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_token_header: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Refreshes an access token using a valid refresh token.
    """
    if not refresh_token_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    refresh_token = refresh_token_header.split(" ")[1]

    try:
        payload = decode_token(refresh_token)
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("sub")

        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token or token type.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_uuid = uuid.UUID(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    new_access_token = create_access_token(data={"user_id": str(user.id)})
    new_refresh_token = create_refresh_token(data={"user_id": str(user.id)})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/users/all", response_model=List[UserProfileResponse])
async def get_all_users(db: AsyncSession = Depends(get_db_session)):
    """
    Retrieves a list of all users.
    NOTE: This endpoint should be protected and restricted to admin users in a production environment.
    """
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieves the profile of the currently authenticated user.
    Requires a valid access token.
    """
    return UserProfileResponse.model_validate(current_user)
