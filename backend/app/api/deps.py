from fastapi import Depends, Header, HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM, create_access_token, decode_access_token, get_token_remaining_seconds
from app.models.user import User

# Issue a refreshed token when less than 30 minutes remain, so active users
# never get logged out mid-session (sliding session without a refresh-token endpoint).
_SLIDING_THRESHOLD_SECONDS = 30 * 60


async def get_current_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = auth_header.removeprefix("Bearer ")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if get_token_remaining_seconds(token) < _SLIDING_THRESHOLD_SECONDS:
        response.headers["X-Refresh-Token"] = create_access_token(str(user.id))

    return user


async def get_optional_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ")
    user_id = decode_access_token(token)
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and get_token_remaining_seconds(token) < _SLIDING_THRESHOLD_SECONDS:
        response.headers["X-Refresh-Token"] = create_access_token(str(user.id))
    return user


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Защита админских эндпоинтов: JWT с role=admin (выдаётся по ADMIN_SECRET)."""
    if not x_admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        payload = jwt.decode(x_admin_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
    except JWTError:
        raise HTTPException(status_code=403, detail="Forbidden")
