"""Integration tests for E2EE endpoints: /setup-e2ee and /recover-access."""
import os

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.e2ee_service import E2EEService


FERNET_KEY = os.environ["FERNET_KEY"]

_FAKE_PUBLIC_KEY = "base64encodedX25519publickey=="
_FAKE_BACKUP_BLOB = "AES-GCM-encrypted-private-key-blob=="


# ---------------------------------------------------------------------------
# /setup-e2ee
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_e2ee_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    auth_headers: dict[str, str],
):
    resp = await client.post(
        "/api/v1/auth/setup-e2ee",
        json={"public_key": _FAKE_PUBLIC_KEY, "encrypted_backup": _FAKE_BACKUP_BLOB},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    await db_session.refresh(user)
    assert user.public_key == _FAKE_PUBLIC_KEY
    assert user.consent_timestamp is not None
    assert user.consent_ip is not None

    # Backup blob должен быть обёрнут Fernet-слоем сервера
    assert user.private_key_backup_encrypted is not None
    decrypted = E2EEService.decrypt_with_fernet(
        user.private_key_backup_encrypted, FERNET_KEY
    )
    assert decrypted == _FAKE_BACKUP_BLOB


@pytest.mark.asyncio
async def test_setup_e2ee_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/setup-e2ee",
        json={"public_key": _FAKE_PUBLIC_KEY, "encrypted_backup": _FAKE_BACKUP_BLOB},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_setup_e2ee_overwrites_existing_keys(
    client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    auth_headers: dict[str, str],
):
    """Повторный вызов /setup-e2ee обновляет ключи (rotate scenario)."""
    # Первый вызов
    await client.post(
        "/api/v1/auth/setup-e2ee",
        json={"public_key": _FAKE_PUBLIC_KEY, "encrypted_backup": _FAKE_BACKUP_BLOB},
        headers=auth_headers,
    )

    new_public_key = "newX25519publickey=="
    new_backup_blob = "new-AES-GCM-blob=="

    resp = await client.post(
        "/api/v1/auth/setup-e2ee",
        json={"public_key": new_public_key, "encrypted_backup": new_backup_blob},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    await db_session.refresh(user)
    assert user.public_key == new_public_key
    decrypted = E2EEService.decrypt_with_fernet(
        user.private_key_backup_encrypted, FERNET_KEY
    )
    assert decrypted == new_backup_blob


# ---------------------------------------------------------------------------
# /recover-access
# ---------------------------------------------------------------------------


async def _setup_user_with_backup(
    db_session: AsyncSession,
    email: str,
    blob: str,
    fernet_key: str,
) -> User:
    """Создаёт пользователя с Fernet-wrapped backup blob в БД."""
    encrypted = E2EEService.encrypt_with_fernet(blob, fernet_key)
    u = User(
        email=email,
        public_key=_FAKE_PUBLIC_KEY,
        private_key_backup_encrypted=encrypted,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.mark.asyncio
async def test_recover_access_success(
    client: AsyncClient,
    db_session: AsyncSession,
):
    blob = "phrase-encrypted-private-key=="
    await _setup_user_with_backup(db_session, "recover@example.com", blob, FERNET_KEY)

    resp = await client.post(
        "/api/v1/auth/recover-access",
        json={"email": "recover@example.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Сервер снял Fernet-слой — возвращает blob зашифрованный фразой юзера
    assert data["backup_encrypted"] == blob
    assert "message" in data


@pytest.mark.asyncio
async def test_recover_access_case_insensitive_email(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Email нормализуется к lower-case перед поиском."""
    blob = "phrase-encrypted-private-key=="
    await _setup_user_with_backup(db_session, "recover2@example.com", blob, FERNET_KEY)

    resp = await client.post(
        "/api/v1/auth/recover-access",
        json={"email": "RECOVER2@EXAMPLE.COM"},
    )
    assert resp.status_code == 200
    assert resp.json()["backup_encrypted"] == blob


@pytest.mark.asyncio
async def test_recover_access_user_not_found(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/recover-access",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 400
    assert "недоступен" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_recover_access_no_backup(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Пользователь есть, но /setup-e2ee не вызывался — backup отсутствует."""
    u = User(email="nobackup@example.com")
    db_session.add(u)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/recover-access",
        json={"email": "nobackup@example.com"},
    )
    assert resp.status_code == 400
    assert "недоступен" in resp.json()["detail"]
