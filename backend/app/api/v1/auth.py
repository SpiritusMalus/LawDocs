from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, generate_magic_token
from app.models.user import User
from app.schemas.user import MagicLinkRequest, UserOut
from app.services.email import send_magic_link

router = APIRouter()


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
async def request_magic_link(
    body: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=body.email)
        db.add(user)

    token = generate_magic_token()
    user.magic_token = token
    user.magic_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
    )
    await db.commit()

    magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"
    await send_magic_link(email=body.email, url=magic_url)


@router.get("/verify")
async def verify_magic_link(
    token: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    result = await db.execute(select(User).where(User.magic_token == token))
    user = result.scalar_one_or_none()

    if not user or not user.magic_token_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    expires_at = user.magic_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link expired")

    user.magic_token = None
    user.magic_token_expires_at = None
    await db.commit()

    access_token = create_access_token(user.id)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie("access_token")
