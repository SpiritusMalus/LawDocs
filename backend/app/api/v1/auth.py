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
from app.core.security import create_access_token, generate_magic_token, hash_magic_token, verify_magic_token
from app.models.order import Order
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


class ContactOut(BaseModel):
    full_name: str = ""
    phone: str = ""
    contact_address: str = ""
    email: str = ""


@router.get("/me/contact", response_model=ContactOut)
async def get_my_contact(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    orders = result.scalars().all()
    form_data: dict = {}
    for order in orders:
        if order.form_data and isinstance(order.form_data, dict):
            form_data = order.form_data
            break
    return ContactOut(
        full_name=form_data.get("full_name", ""),
        phone=form_data.get("phone", ""),
        contact_address=form_data.get("contact_address", ""),
        email=str(current_user.email),
    )


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def request_magic_link(
    request: Request,
    body: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    email_domain = body.email.split("@")[-1] if "@" in body.email else "unknown"
    ip = request.client.host if request.client else "unknown"

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always create or update user (don't reveal if user exists)
    if not user:
        user = User(email=body.email)
        db.add(user)

    token = generate_magic_token()
    user.magic_token = hash_magic_token(token)
    user.magic_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
    )
    await db.commit()

    logger.info("magic_link_requested", extra={"action": "magic_link_requested", "email_domain": email_domain, "ip": ip})

    magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"
    try:
        await send_magic_link(email=body.email, url=magic_url)
        logger.info("magic_link_sent", extra={"action": "magic_link_sent", "email_domain": email_domain})
    except Exception as exc:
        logger.error("magic_link_send_failed", extra={"action": "magic_link_send_failed", "email_domain": email_domain}, exc_info=True)
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
    if not token:
        logger.warning("magic_link_verify_invalid", extra={"action": "magic_link_verify", "reason": "missing_token"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    token_hash = hash_magic_token(token)
    result = await db.execute(select(User).where(User.magic_token == token_hash))
    user = result.scalar_one_or_none()

    if not user or not user.magic_token_expires_at:
        logger.warning("magic_link_verify_invalid", extra={"action": "magic_link_verify", "reason": "invalid_token"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    expires_at = user.magic_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        logger.warning("magic_link_verify_expired", extra={"action": "magic_link_verify", "reason": "expired", "user_id": str(user.id)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link expired")

    user.magic_token = None
    user.magic_token_expires_at = None
    await db.commit()

    logger.info("magic_link_verified", extra={"action": "magic_link_verified", "user_id": str(user.id)})

    access_token = create_access_token(user.id)
    return VerifyOut(
        access_token=access_token,
        order_id=order,
        user=UserOut.model_validate(user),
    )


