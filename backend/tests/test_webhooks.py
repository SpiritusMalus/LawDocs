"""Integration tests for YooKassa webhook."""
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.order import Order
from app.models.user import User


_YOOKASSA_IP = "185.71.76.1"  # valid YooKassa CIDR 185.71.76.0/27

FORM_DATA = {
    "full_name": "Тест Тестович",
    "phone": "+79009999999",
    "contact_address": "г. Тест",
    "email": "webhook@example.com",
    "shop_name": "МагазинТест",
    "purchase_date": "01.01.2025",
    "purchase_amount": "3000",
    "problem_description": "Не работает",
    "problem_type": "defect",
    "request_type": "refund",
}


def _webhook_body(payment_id: str) -> str:
    return json.dumps({
        "event": "payment.succeeded",
        "object": {"id": payment_id},
    })


@pytest.mark.asyncio
async def test_webhook_non_payment_event_accepted(client: AsyncClient):
    body = json.dumps({"event": "payment.canceled", "object": {"id": "pay-000"}})
    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"received": True}


@pytest.mark.asyncio
async def test_webhook_invalid_json_returns_400(client: AsyncClient):
    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_wrong_ip_rejected_in_production(
    client: AsyncClient, monkeypatch
):
    import app.api.v1.webhooks as wh_mod
    monkeypatch.setattr(wh_mod.settings, "APP_ENV", "production")

    body = _webhook_body("pay-999")
    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        content=body,
        headers={"Content-Type": "application/json", "x-real-ip": "1.2.3.4"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_happy_path_order_becomes_done(
    client: AsyncClient,
    db_session: AsyncSession,
    user: User,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="pending_payment",
        yookassa_payment_id="pay-happy-001",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    with (
        patch("app.api.v1.webhooks.fill_template", new_callable=AsyncMock, return_value="Текст претензии"),
        patch("app.api.v1.webhooks.generate_document", new_callable=AsyncMock, return_value=("doc.docx", "doc.pdf")),
        patch("app.api.v1.webhooks.fill_instruction", new_callable=AsyncMock, return_value="Инструкция"),
        patch("app.api.v1.webhooks.generate_instruction", new_callable=AsyncMock, return_value="instr.pdf"),
        patch("app.api.v1.webhooks.download_bytes", new_callable=AsyncMock, return_value=b"%PDF-1.4"),
        patch("app.api.v1.webhooks.send_document_ready", new_callable=AsyncMock),
    ):
        resp = await client.post(
            "/api/v1/webhooks/yookassa",
            content=_webhook_body("pay-happy-001"),
            headers={"Content-Type": "application/json", "x-real-ip": _YOOKASSA_IP},
        )

    assert resp.status_code == 200
    assert resp.json()["received"] is True

    await db_session.refresh(order)
    assert order.status == "done"
    assert order.payment_url is None


@pytest.mark.asyncio
async def test_webhook_duplicate_event_skipped(
    client: AsyncClient,
    db_session: AsyncSession,
    user: User,
):
    # Order already in 'done' state — SKIP LOCKED won't find it as 'pending_payment'
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="done",
        yookassa_payment_id="pay-dup-002",
    )
    db_session.add(order)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/webhooks/yookassa",
        content=_webhook_body("pay-dup-002"),
        headers={"Content-Type": "application/json", "x-real-ip": _YOOKASSA_IP},
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True

    await db_session.refresh(order)
    assert order.status == "done"


@pytest.mark.asyncio
async def test_webhook_generation_failure_sets_failed_status(
    client: AsyncClient,
    db_session: AsyncSession,
    user: User,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="pending_payment",
        yookassa_payment_id="pay-fail-003",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    with (
        patch("app.api.v1.webhooks.fill_template", new_callable=AsyncMock, side_effect=RuntimeError("GigaChat down")),
        patch("app.api.v1.webhooks.send_document_failed", new_callable=AsyncMock),
    ):
        resp = await client.post(
            "/api/v1/webhooks/yookassa",
            content=_webhook_body("pay-fail-003"),
            headers={"Content-Type": "application/json", "x-real-ip": _YOOKASSA_IP},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True
    assert data.get("error") == "generation_failed"

    await db_session.refresh(order)
    assert order.status == "failed"
