"""
ЮKassa: создание платежа, верификация webhook.
Документация: https://yookassa.ru/developers/api
"""

import uuid

import httpx

from app.core.config import settings

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
