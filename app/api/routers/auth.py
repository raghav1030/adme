from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import AsyncSession, get_db_session
from app.models.user import User
from app.core.security import encrypt_token
from githubkit import GitHub, OAuthAppAuthStrategy, OAuthTokenAuthStrategy
from githubkit.versions.latest.models import PublicUser, PrivateUser
from sqlalchemy import select

router = APIRouter()


class AuthResponse(BaseModel):
    message: str
    github_user_id: str


@router.get("/login")
async def github_login():
    github_auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"redirect_uri={settings.GITHUB_REDIRECT_URI}&"
        f"scope=user,repo&"
        f"state={settings.APP_SECRET_KEY}"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/github/callback", response_model=AuthResponse)
async def github_callback(
    request: Request, code: str, state: str, db: AsyncSession = Depends(get_db_session)
):
    # Verify state to prevent CSRF
    if state != settings.APP_SECRET_KEY:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Check if session already has an access token
    session = request.session
    access_token = session.get("access_token")
    if access_token:
        # Validate existing token
        try:
            github = GitHub(
                OAuthAppAuthStrategy(
                    settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET
                )
            )
            user_github = github.with_auth(
                OAuthTokenAuthStrategy(
                    settings.GITHUB_CLIENT_ID,
                    settings.GITHUB_CLIENT_SECRET,
                    token=access_token,
                )
            )
            resp = user_github.rest.users.get_authenticated()
            user_data: PublicUser | PrivateUser = resp.parsed_data
            github_user_id = str(user_data.id)
            return AuthResponse(
                message="Successfully authenticated", github_user_id=github_user_id
            )
        except githubkit.exception.RequestFailed:
            session.pop("access_token", None)  # Clear invalid token

    # Exchange code for access token
    try:
        github = GitHub(
            OAuthAppAuthStrategy(
                settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET
            )
        )
        auth = github.auth.as_web_user(code).exchange_token(github)
        access_token = auth.token
        refresh_token = auth.refresh_token
        token_type = auth.token_type
        scope = auth.scope
    except githubkit.exception.RequestFailed as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to exchange code for token: {str(e)}"
        )

    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    # Store access token in session
    session["access_token"] = access_token

    # Get user info
    try:
        user_github = github.with_auth(
            OAuthTokenAuthStrategy(
                settings.GITHUB_CLIENT_ID,
                settings.GITHUB_CLIENT_SECRET,
                token=access_token,
            )
        )
        resp = user_github.rest.users.get_authenticated()
        user_data: PublicUser | PrivateUser = resp.parsed_data
        github_user_id = str(user_data.id)
    except githubkit.exception.RequestFailed as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to get user info: {str(e)}"
        )

    # Encrypt tokens for database storage
    encrypted_access_token = encrypt_token(access_token)
    encrypted_refresh_token = encrypt_token(refresh_token) if refresh_token else None

    # Store or update user in database
    stmt = select(User).where(User.github_user_id == github_user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            github_user_id=github_user_id,
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            token_type=token_type,
            scope=scope,
        )
        db.add(user)
    else:
        user.access_token = encrypted_access_token
        user.refresh_token = encrypted_refresh_token
        user.token_type = token_type
        user.scope = scope

    await db.commit()

    return AuthResponse(
        message="Successfully authenticated", github_user_id=github_user_id
    )
