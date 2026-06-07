import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthChallenge(Base):
    """Одноразовый challenge для логина по ключу (challenge-response).

    Сервер шифрует случайный nonce публичным ключом и хранит здесь только его
    хэш + сам публичный ключ + срок жизни. Владелец приватного ключа
    расшифровывает nonce и возвращает его → сервер сверяет хэш и помечает
    challenge использованным (single-use). Приватный ключ сервер не видит.
    """

    __tablename__ = "auth_challenges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Публичный ключ, на который зашифрован nonce — по нему ищем юзера на verify.
    public_key: Mapped[str] = mapped_column(String, nullable=False)
    # SHA-256 от nonce: сам nonce в БД не храним, сверяем по хэшу.
    nonce_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Проставляется при успешном verify → повторное использование невозможно.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
