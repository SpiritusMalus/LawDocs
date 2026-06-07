"""Integration tests for keyring-under-password (account = second door to keys)."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.user_key import UserKey


@pytest.mark.asyncio
async def test_password_login_success(client: AsyncClient, db_session: AsyncSession):
    user = User(email="pw@example.com", password_hash=hash_password("correct horse"))
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserKey(user_id=user.id, public_key="PUBKEY_A", wrapped_private_key="WRAPPED_A", label="primary")
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/password-login",
        json={"email": "pw@example.com", "password": "correct horse"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["email"] == "pw@example.com"
    assert len(data["keyring"]) == 1
    assert data["keyring"][0]["public_key"] == "PUBKEY_A"
    assert data["keyring"][0]["wrapped_private_key"] == "WRAPPED_A"


@pytest.mark.asyncio
async def test_password_login_wrong_password_returns_401(client: AsyncClient, db_session: AsyncSession):
    db_session.add(User(email="pw2@example.com", password_hash=hash_password("right-pass-1")))
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/password-login",
        json={"email": "pw2@example.com", "password": "wrong-pass-9"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_password_login_unknown_email_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/password-login",
        json={"email": "nobody@example.com", "password": "whatever-pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_password_login_no_password_set_returns_401(client: AsyncClient, db_session: AsyncSession):
    """Юзер есть (например только magic-link), но пароль не ставил → 401."""
    db_session.add(User(email="nopw@example.com"))
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/password-login",
        json={"email": "nopw@example.com", "password": "some-password"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_set_password_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/set-password",
        json={"password": "new-password-1", "wrapped_keys": []},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_set_password_stores_hash_and_keyring(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    resp = await client.post(
        "/api/v1/auth/set-password",
        headers=auth_headers,
        json={
            "password": "device-password-1",
            "wrapped_keys": [
                {"public_key": "PUB1", "wrapped_private_key": "WRAP1", "label": "primary"}
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["keys_stored"] == 1

    await db_session.refresh(user)
    assert user.password_hash

    result = await db_session.execute(select(UserKey).where(UserKey.user_id == user.id))
    keys = result.scalars().all()
    assert len(keys) == 1
    assert keys[0].public_key == "PUB1"

    # Полный цикл: тем же паролем теперь логинимся по email.
    login = await client.post(
        "/api/v1/auth/password-login",
        json={"email": user.email, "password": "device-password-1"},
    )
    assert login.status_code == 200
    assert len(login.json()["keyring"]) == 1


@pytest.mark.asyncio
async def test_set_password_upserts_same_pubkey(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    """Повторная установка с тем же public_key обновляет blob, не плодит строки."""
    for wrapped in ("WRAP_OLD", "WRAP_NEW"):
        resp = await client.post(
            "/api/v1/auth/set-password",
            headers=auth_headers,
            json={
                "password": "rotating-password",
                "wrapped_keys": [{"public_key": "PUBX", "wrapped_private_key": wrapped}],
            },
        )
        assert resp.status_code == 200

    result = await db_session.execute(select(UserKey).where(UserKey.user_id == user.id))
    keys = result.scalars().all()
    assert len(keys) == 1
    assert keys[0].wrapped_private_key == "WRAP_NEW"
