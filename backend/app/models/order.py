import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import OrderStatus
from app.core.fernet import EncryptedJSON


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)

    situation_id: Mapped[str] = mapped_column(String, nullable=False)

    # Статус: см. OrderStatus (app/core/enums.py). Колонка остаётся String —
    # OrderStatus(str, Enum) сериализуется как строка, миграция не нужна.
    status: Mapped[str] = mapped_column(String, nullable=False, default=OrderStatus.DRAFT.value)

    # Сумма в копейках (199 ₽ = 19900)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=19900)

    # ЮKassa
    yookassa_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Адрес для уведомлений по этому заказу. Отвязан от identity юзера: пользователь
    # может опечататься в почте и поправить её на странице заказа, не перезаполняя форму
    # и не трогая логин-почту аккаунта. NULL → падаем на user.email (см. notification_target).
    notification_email: Mapped[str | None] = mapped_column(String, nullable=True)

    # Данные из wizard-формы (вопросы + ответы пользователя) — хранятся в зашифрованном виде (152-ФЗ)
    form_data: Mapped[dict] = mapped_column(EncryptedJSON, nullable=False, default=dict)

    auto_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Факт явного согласия (оферта + обработка ПДн), проставленного галочкой на
    # финале визарда. Одна запись покрывает оба согласия. Nullable — старые заказы
    # без согласия остаются валидными. Версию штампует сервер (app/core/consent.py).
    offer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_accepted_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    offer_version: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="orders")  # noqa: F821
    document: Mapped["Document | None"] = relationship("Document", back_populates="order", uselist=False)  # noqa: F821

    @property
    def notification_target(self) -> str:
        """Куда слать письма по заказу: per-order адрес, иначе identity-почта юзера.

        Требует загруженного self.user (selectinload) при падении на user.email.
        """
        return self.notification_email or self.user.email
