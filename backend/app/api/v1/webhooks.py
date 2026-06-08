import ipaddress
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.order import Order
from app.services.generation import run_document_release
from app.services.payment import (
    claim_paid_order,
    record_payment_event,
    verify_payment_succeeded,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Актуальный список IP ЮKassa для webhook-уведомлений (док-ция yookassa.ru).
# 77.75.154.128/25 добавлен: реальные уведомления приходили с 77.75.154.206,
# не покрытого старым списком, и отвергались как 403 → оплата не подтверждалась.
_YOOKASSA_CIDRS = [
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.154.128/25"),
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


@router.post("/yookassa", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def yookassa_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
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

    event_type = event.get("event")
    if event_type != "payment.succeeded":
        return {"received": True}

    payment_id = event["object"]["id"]

    # Verify payment status via YooKassa API (prevents fake webhook attacks)
    if not await verify_payment_succeeded(payment_id):
        logger.warning("Webhook payment verification failed for payment_id=%s", payment_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment verification failed")

    # Атомарный идемпотентный захват заказа PENDING_PAYMENT → PAID (см. claim_paid_order).
    claimed = await claim_paid_order(db, payment_id)

    if claimed:
        order_id, user_email = claimed
        outcome, event_order_id = "processed", order_id
    else:
        # Заказ не захвачен: либо уже оплачен (дубль-вебхук), либо payment_id
        # не сопоставлен ни одному заказу (dead-letter).
        order_exists = await db.scalar(
            select(Order.id).where(Order.yookassa_payment_id == payment_id)
        )
        outcome, event_order_id = ("duplicate" if order_exists else "unmatched"), None

    # Журнал событий: идемпотентность на уровне БД + dead-letter. Дубль (UNIQUE
    # payment_id+event_type) → release не запускаем повторно.
    inserted = await record_payment_event(
        db, payment_id, event_type, order_id=event_order_id, outcome=outcome
    )
    if outcome == "unmatched":
        logger.warning(
            "webhook_unmatched_payment",
            extra={"action": "webhook_unmatched_payment", "payment_id": payment_id},
        )

    # Документ уже сгенерирован ДО оплаты (PREVIEW_READY) — здесь только «отпускаем»
    # его (DONE + письмо + шифрование под ключ юзера). Уходит в фон: YooKassa получает
    # 200 сразу. release сам холодно фолбэкнет на полную генерацию, если документа нет.
    if claimed and inserted:
        background_tasks.add_task(
            run_document_release,
            order_id=order_id,
            user_email=user_email,
        )

    return {"received": True}
