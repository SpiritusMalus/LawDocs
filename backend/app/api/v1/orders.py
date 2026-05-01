from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut, PaymentOut
from app.services.payment import create_payment

router = APIRouter()


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentOut:
    order = Order(
        user_id=current_user.id,
        situation_id=body.situation_id,
        form_data=body.form_data,
    )
    db.add(order)
    await db.flush()  # get order.id before payment

    payment_url = await create_payment(order_id=order.id, amount=order.amount)
    order.yookassa_payment_id = payment_url["payment_id"]
    await db.commit()

    return PaymentOut(order_id=order.id, payment_url=payment_url["confirmation_url"])


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
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
