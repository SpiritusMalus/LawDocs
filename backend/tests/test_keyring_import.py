"""Integration tests for key merging (importing key-files into the keyring)."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.user_key import UserKey


def _import_body(password: str, *pubkeys: str) -> dict:
    return {
        "password": password,
        "wrapped_keys": [
            {"public_key": pk, "wrapped_private_key": f"WRAP_{pk}", "label": pk} for pk in pubkeys
        ],
    }


@pytest.mark.asyncio
async def test_import_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/auth/keyring/import", json=_import_body("pw-123456", "P1"))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_import_requires_password_set(client: AsyncClient, auth_headers: dict):
    """Юзер без пароля аккаунта не может импортировать — нечем сверять обёртки."""
    resp = await client.post(
        "/api/v1/auth/keyring/import", headers=auth_headers, json=_import_body("pw-123456", "P1")
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_wrong_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
):
    from app.core.security import create_access_token

    user = User(email="imp@example.com", password_hash=hash_password("real-password-1"))
    db_session.add(user)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    resp = await client.post(
        "/api/v1/auth/keyring/import", headers=headers, json=_import_body("wrong-password-9", "P1")
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_import_adds_keys_and_dedups(client: AsyncClient, db_session: AsyncSession):
    from app.core.security import create_access_token

    user = User(email="imp2@example.com", password_hash=hash_password("merge-password"))
    db_session.add(user)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    first = await client.post(
        "/api/v1/auth/keyring/import", headers=headers, json=_import_body("merge-password", "P1", "P2")
    )
    assert first.status_code == 200
    assert first.json()["total_keys"] == 2

    # Повторный импорт P2 + новый P3 → P2 не дублируется, итого 3.
    second = await client.post(
        "/api/v1/auth/keyring/import", headers=headers, json=_import_body("merge-password", "P2", "P3")
    )
    assert second.status_code == 200
    assert second.json()["total_keys"] == 3

    result = await db_session.execute(select(UserKey).where(UserKey.user_id == user.id))
    pubkeys = sorted(k.public_key for k in result.scalars().all())
    assert pubkeys == ["P1", "P2", "P3"]


@pytest.mark.asyncio
async def test_list_keyring_returns_metadata_only(client: AsyncClient, db_session: AsyncSession):
    from app.core.security import create_access_token

    user = User(email="list@example.com", password_hash=hash_password("list-password"))
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserKey(user_id=user.id, public_key="PK1", wrapped_private_key="SECRET1", label="a"))
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    resp = await client.get("/api/v1/auth/keyring", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["keys"] == [{"public_key": "PK1", "label": "a"}]
    # Обёрнутый ключ не утекает в листинг.
    assert "SECRET1" not in resp.text
