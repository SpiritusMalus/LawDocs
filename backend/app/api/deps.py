from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, get_token_remaining_seconds
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
