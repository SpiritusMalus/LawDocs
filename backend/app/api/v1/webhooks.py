import ipaddress
import json
import logging
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.order import Order
from app.services.generation import run_document_generation

logger = logging.getLogger(__name__)
router = APIRouter()

YOOKASSA_API = "https://api.yookassa.ru/v3"

_YOOKASSA_CIDRS = [
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.156.11/32"),
    ipaddress.ip_network("77.75.156.35/32"),
    ipaddress.ip_network("2a02:5180::/32"),
]


def _is_yookassa_ip(request: Request) -> bool:
    client_host = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(client_host).is_private:
            ip_str = request.headers.get("x-real-ip", client_host)
        else:
            ip_str = client_host
        ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False
    return any(ip in cidr for cidr in _YOOKASSA_CIDRS)


async def _verify_payment(payment_id: str) -> bool:
    """Verify payment status by calling back to YooKassa API."""
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        # Dev mode: skip verification
        return True
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{YOOKASSA_API}/payments/{payment_id}",
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        )
        if not resp.is_success:
            logger.error("YooKassa payment verify failed: %s %s", resp.status_code, payment_id)
            return False
        data = resp.json()
        return data.get("status") == "succeeded"


@router.post("/yookassa", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if settings.APP_ENV != "development" and not _is_yookassa_ip(request):
        real_ip = request.headers.get("x-real-ip", request.client.host if request.client else "unknown")
        logger.warning("webhook_ip_rejected", extra={"action": "webhook_ip_rejected", "ip": real_ip})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    body = await request.body()
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Webhook received invalid JSON")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    if event.get("event") != "payment.succeeded":
        return {"received": True}

    payment_id = event["object"]["id"]

    # Verify payment status via YooKassa API (prevents fake webhook attacks)
    if not await _verify_payment(payment_id):
        logger.warning("Webhook payment verification failed for payment_id=%s", payment_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment verification failed")

    # SELECT FOR UPDATE SKIP LOCKED — атомарный захват строки, второй retry не получит её
    result = await db.execute(
        select(Order)
        .where(Order.yookassa_payment_id == payment_id, Order.status == "pending_payment")
        .with_for_update(skip_locked=True)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        return {"received": True}

    # Захватываем нужные значения до commit: после него атрибуты ORM-объекта
    # истекают, а ленивая подгрузка в async-сессии бросит исключение.
    order_id = order.id
    situation_id = order.situation_id
    form_data = order.form_data
    user_email = order.user.email

    order.status = "generating"
    order.paid_at = datetime.now(UTC)
    await db.commit()

    # Единый пайплайн генерации (тот же, что у retry и авто-retry). Сам ловит
    # ошибки, ставит status=failed и шлёт уведомления — поэтому всегда 200.
    await run_document_generation(
        order_id=order_id,
        situation_id=situation_id,
        form_data=form_data,
        user_email=user_email,
    )

    return {"received": True}
