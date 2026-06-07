import base64
import logging
import os
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_magic_token,
    hash_challenge_nonce,
    hash_magic_token,
)
from app.models.auth_challenge import AuthChallenge
from app.models.order import Order
from app.models.user import User
from app.schemas.auth import (
    ContactOut,
    E2EESetupRequest,
    E2EESetupResponse,
    KeyChallengeResponse,
    KeyLoginResponse,
    RecoverAccessResponse,
)
from app.services.e2ee_file import encrypt_for_public_key
from app.schemas.user import UserOut
from app.services.audit_logger import AuditLogger
from app.services.e2ee_service import E2EEService
from app.services.email import send_magic_link

logger = logging.getLogger(__name__)

# Challenge живёт коротко: окна хватает на расшифровку в браузере, но не на
# офлайн-перебор/replay. Single-use гарантируется отметкой used_at.
_KEY_CHALLENGE_TTL_SECONDS = 120
_CHALLENGE_NONCE_LEN = 32


async def request_magic_link(email_normalized: str, ip: str, db: AsyncSession) -> None:
    email_domain = email_normalized.split("@")[-1] if "@" in email_normalized else "unknown"

    result = await db.execute(select(User).where(User.email == email_normalized))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email_normalized)
        db.add(user)

    token = generate_magic_token()
    user.magic_token = hash_magic_token(token)
    user.magic_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
    )
    await db.commit()

    logger.info("magic_link_requested", extra={"action": "magic_link_requested", "email_domain": email_domain, "ip": ip})

    magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"
    try:
        await send_magic_link(email=email_normalized, url=magic_url)
        logger.info("magic_link_sent", extra={"action": "magic_link_sent", "email_domain": email_domain})
    except Exception as exc:
        logger.error("magic_link_send_failed", extra={"action": "magic_link_send_failed", "email_domain": email_domain}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось отправить письмо. Попробуйте ещё раз.",
        ) from exc


async def verify_magic_link(token: str, db: AsyncSession) -> tuple[User, str]:
    if not token:
        logger.warning("magic_link_verify_invalid", extra={"action": "magic_link_verify", "reason": "missing_token"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    token_hash = hash_magic_token(token)
    result = await db.execute(select(User).where(User.magic_token == token_hash))
    user = result.scalar_one_or_none()

    if not user or not user.magic_token_expires_at:
        logger.warning("magic_link_verify_invalid", extra={"action": "magic_link_verify", "reason": "invalid_token"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    expires_at = user.magic_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        logger.warning("magic_link_verify_expired", extra={"action": "magic_link_verify", "reason": "expired", "user_id": str(user.id)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link expired")

    user.magic_token = None
    user.magic_token_expires_at = None
    await db.commit()

    logger.info("magic_link_verified", extra={"action": "magic_link_verified", "user_id": str(user.id)})

    access_token = create_access_token(str(user.id))
    return user, access_token


async def get_user_contact(user: User, db: AsyncSession) -> ContactOut:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    orders = result.scalars().all()
    form_data: dict = {}
    for order in orders:
        if order.form_data and isinstance(order.form_data, dict):
            form_data = order.form_data
            break
    return ContactOut(
        full_name=form_data.get("full_name", ""),
        phone=form_data.get("phone", ""),
        contact_address=form_data.get("contact_address", ""),
        address_city=form_data.get("address_city", ""),
        address_street=form_data.get("address_street", ""),
        address_house=form_data.get("address_house", ""),
        address_building=form_data.get("address_building", ""),
        address_structure=form_data.get("address_structure", ""),
        address_apartment=form_data.get("address_apartment", ""),
        email=str(user.email),
    )


async def setup_e2ee(user: User, body: E2EESetupRequest, ip: str, db: AsyncSession) -> E2EESetupResponse:
    try:
        user.public_key = body.public_key

        try:
            server_encrypted_backup = E2EEService.encrypt_with_fernet(
                body.encrypted_backup, settings.FERNET_KEY
            )
            user.private_key_backup_encrypted = server_encrypted_backup
        except Exception as e:
            logger.error("e2ee_backup_encryption_failed", extra={"action": "e2ee_setup", "user_id": str(user.id), "error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при сохранении backup ключа",
            ) from e

        user.consent_timestamp = datetime.now(UTC)
        user.consent_ip = ip
        user.consent_version = "2.0"

        await db.commit()

        await AuditLogger.log_access(
            session=db,
            user_id=user.id,
            action="e2ee_setup_complete",
            data_type="private_key_backup",
            ip_address=ip,
            details={"public_key_saved": True, "backup_stored": True},
        )

        logger.info("e2ee_setup_complete", extra={"action": "e2ee_setup_complete", "user_id": str(user.id), "ip": ip})

        return E2EESetupResponse(
            status="success",
            message="Ключи сохранены. Документы будут зашифрованы вашим ключом.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("e2ee_setup_failed", extra={"action": "e2ee_setup", "user_id": str(user.id)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при сохранении E2EE настроек",
        ) from e


async def recover_access(email_normalized: str, ip: str, db: AsyncSession) -> RecoverAccessResponse:
    try:
        result = await db.execute(select(User).where(User.email == email_normalized))
        user = result.scalar_one_or_none()

        if not user or not user.private_key_backup_encrypted:
            if not user:
                logger.warning("recover_access_user_not_found", extra={"action": "recover_access", "email_domain": email_normalized.split("@")[-1], "ip": ip})
            else:
                logger.warning("recover_access_no_backup", extra={"action": "recover_access", "user_id": str(user.id), "ip": ip})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backup ключ недоступен",
            )

        try:
            blob_encrypted_by_phrase = E2EEService.decrypt_with_fernet(
                user.private_key_backup_encrypted, settings.FERNET_KEY
            )

            await AuditLogger.log_access(
                session=db,
                user_id=user.id,
                action="key_recovery_attempt",
                data_type="private_key_backup",
                ip_address=ip,
                details={"success": True},
            )

            logger.info("key_recovery_blob_sent", extra={"action": "key_recovery_success", "user_id": str(user.id), "ip": ip})

            return RecoverAccessResponse(
                backup_encrypted=blob_encrypted_by_phrase,
                message="Расшифруйте ключ своей парольной фразой в браузере.",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("key_recovery_decryption_failed", extra={"action": "key_recovery", "user_id": str(user.id)}, exc_info=True)

            await AuditLogger.log_access(
                session=db,
                user_id=user.id,
                action="key_recovery_attempt",
                data_type="private_key_backup",
                ip_address=ip,
                details={"success": False, "error": "decryption_failed"},
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при восстановлении доступа",
            ) from e

    except HTTPException:
        raise
    except Exception as e:
        logger.error("recover_access_failed", extra={"action": "recover_access"}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при восстановлении доступа",
        ) from e


# ============================================================================
# LOGIN BY KEY — challenge-response на keypair
# ============================================================================


async def issue_key_challenge(public_key: str, ip: str, db: AsyncSession) -> KeyChallengeResponse:
    """Шлёт challenge: случайный nonce, зашифрованный публичным ключом.

    Челлендж выдаём ВСЕГДА (даже если под этим ключом нет аккаунта) — иначе ответ
    раскрывал бы существование аккаунта (enumeration). Существование проверяется
    только на verify, обобщённой 401.
    """
    try:
        nonce = os.urandom(_CHALLENGE_NONCE_LEN)
        encrypted_challenge = encrypt_for_public_key(nonce, public_key)
    except Exception as exc:
        # Битый/невалидный public_key — не наша ошибка, отвечаем 400.
        logger.warning("key_challenge_bad_pubkey", extra={"action": "key_challenge", "ip": ip})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный публичный ключ",
        ) from exc

    challenge = AuthChallenge(
        public_key=public_key,
        nonce_hash=hash_challenge_nonce(nonce),
        expires_at=datetime.now(UTC) + timedelta(seconds=_KEY_CHALLENGE_TTL_SECONDS),
    )
    db.add(challenge)
    await db.commit()

    logger.info("key_challenge_issued", extra={"action": "key_challenge", "challenge_id": challenge.id, "ip": ip})
    return KeyChallengeResponse(challenge_id=challenge.id, encrypted_challenge=encrypted_challenge)


async def key_login(challenge_id: str, nonce_b64: str, ip: str, db: AsyncSession) -> KeyLoginResponse:
    """Проверяет расшифрованный nonce и логинит юзера по публичному ключу.

    Single-use: на успехе помечаем challenge used_at. Существование аккаунта и
    верность nonce неотличимы для клиента — везде обобщённая 401.
    """
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не удалось войти по ключу")

    result = await db.execute(select(AuthChallenge).where(AuthChallenge.id == challenge_id))
    challenge = result.scalar_one_or_none()
    if challenge is None or challenge.used_at is not None:
        raise invalid

    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise invalid

    try:
        presented = base64.b64decode(nonce_b64, validate=True)
    except Exception as exc:
        raise invalid from exc
    if hash_challenge_nonce(presented) != challenge.nonce_hash:
        raise invalid

    # Челлендж решён верно — сжигаем его (даже если юзера под ключом нет).
    challenge.used_at = datetime.now(UTC)

    user_result = await db.execute(select(User).where(User.public_key == challenge.public_key))
    user = user_result.scalars().first()
    if user is None:
        await db.commit()
        logger.warning("key_login_no_account", extra={"action": "key_login", "ip": ip})
        raise invalid

    await db.commit()
    logger.info("key_login_success", extra={"action": "key_login", "user_id": str(user.id), "ip": ip})

    access_token = create_access_token(str(user.id))
    return KeyLoginResponse(access_token=access_token, user=UserOut.model_validate(user))
