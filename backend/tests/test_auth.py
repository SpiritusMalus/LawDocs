"""Integration tests for magic link auth flow."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, generate_magic_token, hash_magic_token
from app.models.user import User


@pytest.mark.asyncio
async def test_verify_magic_link_success(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = generate_magic_token()
    user = User(
        email="magic@example.com",
        magic_token=hash_magic_token(token),
        magic_token_expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    resp = await client.get(f"/api/v1/auth/verify?token={token}")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "magic@example.com"
    assert data["order_id"] is None


@pytest.mark.asyncio
async def test_verify_magic_link_with_order_id(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from app.models.order import Order

    token = generate_magic_token()
    user = User(
        email="magic2@example.com",
        magic_token=hash_magic_token(token),
        magic_token_expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db_session.add(user)
    await db_session.flush()

    order = Order(user_id=user.id, situation_id="shop", form_data={}, status="draft")
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.get(f"/api/v1/auth/verify?token={token}&order={order.id}")
    assert resp.status_code == 200
    assert resp.json()["order_id"] == order.id


@pytest.mark.asyncio
async def test_verify_magic_link_expired_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = generate_magic_token()
    user = User(
        email="expired@example.com",
        magic_token=hash_magic_token(token),
        magic_token_expires_at=datetime.now(UTC) - timedelta(minutes=1),  # already expired
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.get(f"/api/v1/auth/verify?token={token}")
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_magic_link_replay_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token = generate_magic_token()
    user = User(
        email="replay@example.com",
        magic_token=hash_magic_token(token),
        magic_token_expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db_session.add(user)
    await db_session.commit()

    # First use — succeeds, token is cleared
    resp1 = await client.get(f"/api/v1/auth/verify?token={token}")
    assert resp1.status_code == 200

    # Second use — token is already cleared → invalid
    resp2 = await client.get(f"/api/v1/auth/verify?token={token}")
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_verify_magic_link_invalid_token_returns_400(client: AsyncClient):
    resp = await client.get("/api/v1/auth/verify?token=totally_fake_token")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_me_returns_current_user(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == user.email
    assert data["id"] == user.id


@pytest.mark.asyncio
async def test_get_me_without_token_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_request_magic_link_sends_email(
    client: AsyncClient,
    db_session: AsyncSession,
):
    with patch("app.api.v1.auth.send_magic_link", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(
            "/api/v1/auth/magic-link",
            json={"email": "new@example.com"},
        )
    assert resp.status_code == 204
    mock_mail.assert_called_once()


@pytest.mark.asyncio
async def test_get_my_contact_returns_last_order_fields(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    from app.models.order import Order

    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data={
            "full_name": "Иванов Иван",
            "phone": "+79001112233",
            "contact_address": "г. Москва",
        },
        status="done",
    )
    db_session.add(order)
    await db_session.commit()

    resp = await client.get("/api/v1/auth/me/contact", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Иванов Иван"
    assert data["phone"] == "+79001112233"
    assert data["email"] == user.email
