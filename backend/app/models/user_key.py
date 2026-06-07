import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserKey(Base):
    """Keyring аккаунта: приватные ключи, обёрнутые под пароль аккаунта.

    wrapped_private_key шифруется НА КЛИЕНТЕ (PBKDF2 + AES-GCM, тем же паролем,
    что и аккаунт) — сервер хранит непрозрачный blob и расшифровать его не может.
    Один пароль открывает весь keyring → кабинет видит заказы по всем ключам.
    Документы при этом не переподписываются (см. design-блок «MERGING MULTIPLE KEYS»).
    """

    __tablename__ = "user_keys"
    __table_args__ = (UniqueConstraint("user_id", "public_key", name="uq_user_keys_user_pubkey"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    public_key: Mapped[str] = mapped_column(String, nullable=False)
    # blob, зашифрованный паролем на клиенте — сервер его не читает.
    wrapped_private_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Метка для UX («ключ от 5 июня») — необязательна.
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
