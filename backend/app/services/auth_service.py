import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.fernet import _get_fernet
from app.core.security import create_access_token, generate_magic_token, hash_magic_token
from app.models.order import Order
from app.models.user import User
from app.schemas.auth import ContactOut, E2EESetupRequest, E2EESetupResponse, RecoverAccessResponse
from app.schemas.user import UserOut
from app.services.audit_logger import AuditLogger
from app.services.e2ee_service import E2EEService
from app.services.email import send_magic_link

logger = logging.getLogger(__name__)


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
        email=str(user.email),
    )


async def setup_e2ee(user: User, body: E2EESetupRequest, ip: str, db: AsyncSession) -> E2EESetupResponse:
    try:
        user.public_key = body.public_key

        try:
            server_encrypted_backup = E2EEService.encrypt_with_fernet(
                body.encrypted_backup, _get_fernet()
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
                user.private_key_backup_encrypted, _get_fernet()
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
