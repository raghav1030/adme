# app/api/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from jose import JWTError
from sqlalchemy import select
from app.api.core.database import AsyncSession, get_db_session
from app.api.models import User  # Assuming your User model is in app.api.models
from app.api.core.security import decode_token  # Import the decode_token function
import uuid

# OAuth2PasswordBearer is used for password flow, but HTTPBearer is more general for token extraction
oauth2_scheme = HTTPBearer(scheme_name="Bearer")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependency to get the current authenticated user from the access token.
    """
    token = (
        credentials.credentials
    )  # The actual JWT string from the "Bearer <token>" header
    try:
        payload = decode_token(token)
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("sub")

        if user_id is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token or token type.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_uuid = uuid.UUID(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


# You can add more specific dependencies if needed, e.g., for requiring active users
# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     if not current_user.is_active: # Assuming an 'is_active' field in your User model
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
#     return current_user
