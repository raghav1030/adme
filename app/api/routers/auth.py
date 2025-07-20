from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import AsyncSession, get_db_session
from app.models import User, UserOAuth, OAuthProvider
from app.core.security import encrypt_token
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
import httpx

router = APIRouter()


class AuthResponse(BaseModel):
    message: str
    github_user_id: str
    user_id: str


async def ensure_github_provider(db: AsyncSession):
    """Ensure GitHub provider exists in oauth_providers."""
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


@router.get("/login")
async def github_login():
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
        f"scope=user,repo&"
        f"state={settings.APP_SECRET_KEY}"
    )
    return github_auth_url


@router.get("/github/callback", response_model=AuthResponse)
async def github_callback(
    request: Request, code: str, state: str, db: AsyncSession = Depends(get_db_session)
):
    if state != settings.APP_SECRET_KEY:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    await ensure_github_provider(db)

    session = request.session
    access_token = session.get("access_token")
    if access_token:
        async with httpx.AsyncClient() as client:
            try:
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    print("user data", user_data)
                    github_user_id = str(user_data.get("id"))
                    stmt = select(UserOAuth).where(
                        UserOAuth.provider_uid == github_user_id,
                        UserOAuth.provider == "github",
                    )
                    result = await db.execute(stmt)
                    user_oauth = result.scalar_one_or_none()
                    if user_oauth:
                        return AuthResponse(
                            message="Successfully authenticated",
                            github_user_id=github_user_id,
                            user_id=str(user_oauth.user_id),
                        )
                session.pop("access_token", None)
            except httpx.HTTPStatusError:
                session.pop("access_token", None)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        scope = (
            token_data.get("scope", "").split(",") if token_data.get("scope") else []
        )
        expires_at = None

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        session["access_token"] = access_token

        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()
        print("user data", user_data)
        github_user_id = str(user_data.get("id"))
        email = user_data.get("email")
        full_name = user_data.get("name")
        avatar_url = user_data.get("avatar_url")

        if not email:
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if email_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user emails")
            emails = email_response.json()
            primary_email = next((e["email"] for e in emails if e.get("primary")), None)
            email = primary_email or emails[0]["email"] if emails else None

        if not email:
            raise HTTPException(status_code=400, detail="No email found for user")

        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=email, full_name=full_name, avatar_url=avatar_url)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            user.full_name = full_name
            user.avatar_url = avatar_url
            user.updated_at = func.now()
            await db.commit()

        encrypted_access_token = encrypt_token(access_token)
        encrypted_refresh_token = (
            encrypt_token(refresh_token) if refresh_token else None
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
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                scope=scope,
                expires_at=expires_at,
            )
            db.add(user_oauth)
        else:
            user_oauth.provider_uid = github_user_id
            user_oauth.access_token = encrypted_access_token
            user_oauth.refresh_token = encrypted_refresh_token
            user_oauth.scope = scope
            user_oauth.expires_at = expires_at
            user_oauth.created_at = func.now()

        await db.commit()

        return AuthResponse(
            message="Successfully authenticated",
            github_user_id=github_user_id,
            user_id=str(user.id),
            user_data=user_data
        )


@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db_session)):

    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    print(users)
    return users
