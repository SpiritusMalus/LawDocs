"""
ЮKassa: создание платежа, верификация webhook.
Документация: https://yookassa.ru/developers/api
"""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.enums import OrderStatus
from app.models.order import Order
from app.models.payment_event import PaymentEvent

logger = logging.getLogger(__name__)

YOOKASSA_API = "https://api.yookassa.ru/v3"


def _auth() -> tuple[str, str]:
    return settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY


async def create_payment(order_id: str, amount: int, customer_email: str) -> dict:
    """
    Создаёт платёж в ЮKassa.
    amount — в копейках (10000 = 100 ₽).
    Возвращает {"payment_id": ..., "confirmation_url": ...}.
    """
    if not settings.YOOKASSA_SHOP_ID:
        return {
            "payment_id": f"dev_{order_id}",
            "confirmation_url": f"{settings.FRONTEND_URL}/dev/payment?order_id={order_id}",
        }

    rub_amount = f"{amount / 100:.2f}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{YOOKASSA_API}/payments",
            auth=_auth(),
            headers={"Idempotence-Key": str(uuid.uuid4())},
            json={
                "amount": {"value": rub_amount, "currency": "RUB"},
                "capture": True,
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.FRONTEND_URL}/orders/{order_id}",
                },
                "description": f"LawDocs — юридический документ",
                "metadata": {"order_id": order_id},
                "receipt": {
                    "customer": {"email": customer_email},
                    "items": [
                        {
                            "description": "Подготовка юридического документа",
                            "quantity": "1.00",
                            "amount": {"value": rub_amount, "currency": "RUB"},
                            "vat_code": 1,
                            "payment_mode": "full_payment",
                            "payment_subject": "service",
                        }
                    ],
                },
            },
            timeout=15,
        )
        if not resp.is_success:
            raise ValueError(f"YooKassa error {resp.status_code}: {resp.text}")
        data = resp.json()

    return {
        "payment_id": data["id"],
        "confirmation_url": data["confirmation"]["confirmation_url"],
    }


async def refund_payment(payment_id: str, amount: int) -> bool:
    """Возвращает деньги через YooKassa. amount в копейках. Возвращает True если успешно."""
    if not settings.YOOKASSA_SHOP_ID:
        return True  # dev mode
    rub_amount = f"{amount / 100:.2f}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{YOOKASSA_API}/refunds",
            auth=_auth(),
            headers={"Idempotence-Key": str(uuid.uuid4())},
            json={
                "payment_id": payment_id,
                "amount": {"value": rub_amount, "currency": "RUB"},
            },
            timeout=15,
        )
        return resp.is_success


async def verify_payment_succeeded(payment_id: str) -> bool:
    """Спрашивает у ЮKassa реальный статус платежа (защита от поддельных вебхуков).

    В dev-режиме (нет ключей) — True. Единый источник правды для вебхука и для
    reconcile-loop, чтобы оба сверялись с ЮKassa одинаково.
    """
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        return True
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{YOOKASSA_API}/payments/{payment_id}", auth=_auth())
        if not resp.is_success:
            logger.error("yookassa_verify_failed: %s %s", resp.status_code, payment_id)
            return False
        return resp.json().get("status") == "succeeded"


async def claim_paid_order(db: AsyncSession, payment_id: str) -> tuple[str, str] | None:
    """Атомарно переводит заказ PENDING_PAYMENT → PAID по payment_id.

    SELECT ... FOR UPDATE SKIP LOCKED + фильтр по статусу делают операцию
    идемпотентной и безопасной при гонке (вебхук + reconcile + retry): только один
    вызов «захватит» заказ, остальные получат None. Возвращает (order_id, email)
    при успешном захвате, иначе None (уже оплачен / не найден / занят).
    """
    result = await db.execute(
        select(Order)
        .where(
            Order.yookassa_payment_id == payment_id,
            Order.status == OrderStatus.PENDING_PAYMENT.value,
        )
        .with_for_update(skip_locked=True)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        return None
    order_id = order.id
    user_email = order.notification_target
    order.status = OrderStatus.PAID.value
    order.paid_at = datetime.now(UTC)
    await db.commit()
    return order_id, user_email


async def record_payment_event(
    db: AsyncSession,
    payment_id: str,
    event_type: str,
    *,
    order_id: str | None,
    outcome: str,
    source: str = "webhook",
) -> bool:
    """Пишет строку в журнал платёжных событий. Возвращает False, если событие уже
    было (UNIQUE payment_id+event_type) — это дубль-вебхук.

    Журнал даёт идемпотентность на уровне БД и dead-letter (order_id=NULL) для
    несопоставленных событий. Аудит — best-effort: сбой записи не должен ронять
    обработку оплаты.
    """
    event = PaymentEvent(
        payment_id=payment_id,
        event_type=event_type,
        order_id=order_id,
        outcome=outcome,
        source=source,
    )
    db.add(event)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        return False
