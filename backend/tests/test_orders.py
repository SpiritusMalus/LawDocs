"""Integration tests for orders API."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import User


FORM_DATA = {
    "full_name": "Иванов Иван Иванович",
    "phone": "+79001234567",
    "email": "ivan@example.com",
    "store_name": "ТестМаркет",
    "product_name": "Тестовый товар",
    "product_price": "5000",
    "purchase_date": "01.01.2025",
    "problem_desc": "Товар оказался бракованным",
    "problem_type": "defect",
    "demand": "refund",
}


@pytest.mark.asyncio
async def test_init_order_unauthenticated_sends_magic_link(client: AsyncClient):
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(
            "/api/v1/orders/init",
            json={
                "email": "ivan@example.com",
                "situation_id": "shop",
                "form_data": FORM_DATA,
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["requires_verification"] is True
    assert data["redirect_to"] is None
    mock_mail.assert_called_once()


@pytest.mark.asyncio
async def test_init_order_authenticated_skips_magic_link(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={
                "email": "ivan@example.com",
                "situation_id": "shop",
                "form_data": FORM_DATA,
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["requires_verification"] is False
    assert "/orders/" in data["redirect_to"]
    mock_mail.assert_not_called()


@pytest.mark.asyncio
async def test_init_order_unknown_situation_rejected(
    client: AsyncClient,
    auth_headers: dict,
):
    resp = await client.post(
        "/api/v1/orders/init",
        headers=auth_headers,
        json={
            "email": "ivan@example.com",
            "situation_id": "nonexistent_situation",
            "form_data": {},
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pay_order_draft_creates_payment(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="draft",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    fake_payment = {
        "payment_id": "yoo-pay-001",
        "confirmation_url": "https://yookassa.ru/pay/001",
    }
    with patch("app.api.v1.orders.create_payment", new_callable=AsyncMock, return_value=fake_payment):
        resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_url"] == fake_payment["confirmation_url"]

    await db_session.refresh(order)
    assert order.status == "pending_payment"
    assert order.payment_url == fake_payment["confirmation_url"]


@pytest.mark.asyncio
async def test_pay_order_wrong_owner_returns_404(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    other_user = User(email="other@example.com")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    order = Order(
        user_id=other_user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="draft",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pay_order_done_status_rejected(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="done",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_order_returns_order(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="draft",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == order.id
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_orders_returns_user_orders(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    for i in range(3):
        o = Order(user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="draft")
        db_session.add(o)
    await db_session.commit()

    resp = await client.get("/api/v1/orders/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_retry_failed_order_starts_generation(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="failed",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    with patch("app.api.v1.orders.run_document_generation", new_callable=AsyncMock):
        resp = await client.post(f"/api/v1/orders/{order.id}/retry", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "generating"

    await db_session.refresh(order)
    assert order.status == "generating"


@pytest.mark.asyncio
async def test_retry_non_failed_order_returns_404(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="done",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/retry", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/orders/")
    assert resp.status_code == 401
