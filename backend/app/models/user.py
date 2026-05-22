import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completed_orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Magic link
    magic_token: Mapped[str | None] = mapped_column(String, nullable=True)
    magic_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # E2EE fields
    email_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    email_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    name_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    public_key: Mapped[str | None] = mapped_column(String, nullable=True)
    private_key_backup_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    consent_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")  # noqa: F821
