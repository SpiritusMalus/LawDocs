"""Integration tests for login-by-key (challenge-response on the E2EE keypair)."""
import base64
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from nacl.public import Box, PrivateKey, PublicKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_challenge import AuthChallenge
from app.models.user import User


def _new_keypair() -> tuple[PrivateKey, str]:
    """Возвращает (приватный ключ, base64 публичного) — как у фронта (nacl.box)."""
    priv = PrivateKey.generate()
    pub_b64 = base64.b64encode(bytes(priv.public_key)).decode()
    return priv, pub_b64


def _solve(encrypted_challenge_b64: str, priv: PrivateKey) -> str:
    """Расшифровывает nonce приватным ключом → base64 (как solveChallenge на фронте)."""
    blob = base64.b64decode(encrypted_challenge_b64)
    nonce, eph_pub, box_ct = blob[:24], blob[24:56], blob[56:]
    opened = Box(priv, PublicKey(eph_pub)).decrypt(box_ct, nonce)
    return base64.b64encode(opened).decode()


async def _challenge(client: AsyncClient, pub_b64: str) -> dict:
    resp = await client.post("/api/v1/auth/key-challenge", json={"public_key": pub_b64})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_key_login_success(client: AsyncClient, db_session: AsyncSession):
    priv, pub_b64 = _new_keypair()
    user = User(email="keyuser@example.com", public_key=pub_b64)
    db_session.add(user)
    await db_session.commit()

    ch = await _challenge(client, pub_b64)
    nonce = _solve(ch["encrypted_challenge"], priv)

    resp = await client.post(
        "/api/v1/auth/key-login",
        json={"challenge_id": ch["challenge_id"], "nonce": nonce},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["email"] == "keyuser@example.com"


@pytest.mark.asyncio
async def test_key_login_no_account_returns_401(client: AsyncClient):
    """Челлендж решён верно, но под этим ключом нет аккаунта → обобщённая 401."""
    priv, pub_b64 = _new_keypair()
    ch = await _challenge(client, pub_b64)
    nonce = _solve(ch["encrypted_challenge"], priv)

    resp = await client.post(
        "/api/v1/auth/key-login",
        json={"challenge_id": ch["challenge_id"], "nonce": nonce},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_key_login_replay_rejected(client: AsyncClient, db_session: AsyncSession):
    priv, pub_b64 = _new_keypair()
    db_session.add(User(email="replay-key@example.com", public_key=pub_b64))
    await db_session.commit()

    ch = await _challenge(client, pub_b64)
    nonce = _solve(ch["encrypted_challenge"], priv)
    body = {"challenge_id": ch["challenge_id"], "nonce": nonce}

    first = await client.post("/api/v1/auth/key-login", json=body)
    assert first.status_code == 200
    # Single-use: тот же challenge_id повторно не сработает.
    second = await client.post("/api/v1/auth/key-login", json=body)
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_key_login_expired_returns_401(client: AsyncClient, db_session: AsyncSession):
    priv, pub_b64 = _new_keypair()
    db_session.add(User(email="exp-key@example.com", public_key=pub_b64))
    await db_session.commit()

    ch = await _challenge(client, pub_b64)
    nonce = _solve(ch["encrypted_challenge"], priv)

    # Просрочим челлендж вручную.
    result = await db_session.execute(
        select(AuthChallenge).where(AuthChallenge.id == ch["challenge_id"])
    )
    challenge = result.scalar_one()
    challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/key-login",
        json={"challenge_id": ch["challenge_id"], "nonce": nonce},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_key_login_wrong_nonce_returns_401(client: AsyncClient, db_session: AsyncSession):
    priv, pub_b64 = _new_keypair()
    db_session.add(User(email="wrong-nonce@example.com", public_key=pub_b64))
    await db_session.commit()

    ch = await _challenge(client, pub_b64)
    bogus = base64.b64encode(b"\x00" * 32).decode()

    resp = await client.post(
        "/api/v1/auth/key-login",
        json={"challenge_id": ch["challenge_id"], "nonce": bogus},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_key_challenge_invalid_public_key_returns_400(client: AsyncClient):
    resp = await client.post("/api/v1/auth/key-challenge", json={"public_key": "not-base64!!"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_key_challenge_issued_even_without_account(client: AsyncClient):
    """Челлендж выдаётся всегда — иначе ответ раскрывал бы существование аккаунта."""
    _, pub_b64 = _new_keypair()
    ch = await _challenge(client, pub_b64)
    assert ch["challenge_id"]
    assert ch["encrypted_challenge"]
