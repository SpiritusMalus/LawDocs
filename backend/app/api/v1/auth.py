import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, generate_magic_token
from app.models.user import User
from app.schemas.user import MagicLinkRequest, UserOut
from app.services.email import send_magic_link

logger = logging.getLogger(__name__)
router = APIRouter()


class VerifyOut(BaseModel):
    access_token: str
    order_id: str | None = None
    user: UserOut


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def request_magic_link(
    request: Request,
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
    try:
        await send_magic_link(email=body.email, url=magic_url)
    except Exception as exc:
        # Email send failed — token is committed, user can retry or contact support
        logger.error("Failed to send magic link to %s: %s", body.email, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось отправить письмо. Попробуйте ещё раз.",
        ) from exc


@router.get("/verify", response_model=VerifyOut)
@limiter.limit("20/minute")
async def verify_magic_link(
    request: Request,
    token: str,
    order: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> VerifyOut:
    """
    Verifies a magic link token. Returns JWT in body so Next.js Route Handler
    can set the httpOnly cookie for the correct frontend domain.
    """
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
    return VerifyOut(
        access_token=access_token,
        order_id=order,
        user=UserOut.model_validate(user),
    )


