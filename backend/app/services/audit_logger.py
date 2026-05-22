from datetime import datetime
from typing import Any, Optional

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogger:
    """Логирует все операции с E2EE данными для аудита и безопасности"""

    @staticmethod
    async def log_access(
        session: AsyncSession,
        user_id: str,
        action: str,
        data_type: str,
        ip_address: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Логирует доступ к защищённым данным

        Args:
            session: AsyncSession для БД
            user_id: ID пользователя
            action: Тип действия (e.g., "e2ee_setup_complete", "order_created", "key_recovery_attempt")
            data_type: Тип данных (e.g., "form_data_encrypted", "private_key_backup")
            ip_address: IP адрес клиента
            details: Доп. детали (JSON)
        """
        try:
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                data_type=data_type,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                details=details or {},
            )
            session.add(log_entry)
            await session.flush()
        except Exception as e:
            # Логирование ошибок не должно ломать основной поток
            print(f"AuditLog error: {str(e)}")
            pass
