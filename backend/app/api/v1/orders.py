import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import generate_magic_token, hash_magic_token
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderInitOut, OrderInitRequest, OrderListItem, OrderOut, PaymentOut
from app.services.email import send_magic_link
from app.services.payment import create_payment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[OrderListItem])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderListItem]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.document))
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()
    return [
        OrderListItem(
            id=o.id,
            situation_id=o.situation_id,
            status=o.status,
            amount=o.amount,
            created_at=o.created_at,
            has_document=o.document is not None,
        )
        for o in orders
    ]


@router.post("/init", response_model=OrderInitOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def init_order(
    request: Request,
    body: OrderInitRequest,
    db: AsyncSession = Depends(get_db),
) -> OrderInitOut:
    # Upsert user: handle concurrent requests via IntegrityError retry
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=str(body.email))
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            # Concurrent request already created this user — roll back and re-fetch
            await db.rollback()
            result = await db.execute(select(User).where(User.email == body.email))
            user = result.scalar_one()

    order = Order(
        user_id=user.id,
        situation_id=body.situation_id,
        form_data=body.form_data,
        status="draft",
    )
    db.add(order)
    await db.flush()

    logger.info("order_created", extra={"action": "order_created", "order_id": str(order.id), "situation_id": body.situation_id, "user_id": str(user.id)})

    token = generate_magic_token()
    user.magic_token = hash_magic_token(token)
    user.magic_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
    )
    await db.commit()

    magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}&order={order.id}"
    try:
        await send_magic_link(email=str(body.email), url=magic_url)
    except Exception as exc:
        logger.error("order_magic_link_send_failed", extra={"action": "magic_link_send_failed", "order_id": str(order.id)}, exc_info=True)
        if settings.APP_ENV == "development":
            logger.warning("DEV MAGIC LINK: %s", magic_url)
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не удалось отправить письмо. Попробуйте ещё раз.",
            ) from exc

    return OrderInitOut(order_id=order.id)


@router.post("/{order_id}/pay", response_model=PaymentOut)
async def pay_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentOut:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status not in ("draft", "pending_payment"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order not payable")

    payment_data = await create_payment(order_id=order.id, amount=order.amount)
    order.yookassa_payment_id = payment_data["payment_id"]
    order.status = "pending_payment"
    await db.commit()

    logger.info("payment_initiated", extra={"action": "payment_initiated", "order_id": str(order.id), "payment_id": payment_data["payment_id"], "user_id": str(current_user.id)})

    return PaymentOut(order_id=order.id, payment_url=payment_data["confirmation_url"])


@router.get("/{order_id}", response_model=OrderOut)
@limiter.limit("30/minute")
async def get_order(
    request: Request,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
