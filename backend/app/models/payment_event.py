import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentEvent(Base):
    """Журнал входящих платёжных событий ЮKassa — идемпотентность + dead-letter.

    Назначение (system-design §6 «webhook durability»):
    - UNIQUE(payment_id, event_type) даёт идемпотентность на уровне БД: повторный
      вебхук (ретрай ЮKassa) не обрабатывается дважды.
    - order_id = NULL → событие не сопоставлено заказу (dead-letter), видно для разбора.
    - source отличает обычный вебхук от восстановления через reconcile-loop.

    Денежных/ПДн-полей не храним — только идентификаторы и исход.
    """

    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("payment_id", "event_type", name="uq_payment_event"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    # NULL = заказ не найден по payment_id (dead-letter, требует ручного разбора).
    order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # processed | duplicate | unmatched | reconciled
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    # webhook | reconcile
    source: Mapped[str] = mapped_column(String, nullable=False, default="webhook")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
