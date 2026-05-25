import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String, ForeignKey("orders.id"), nullable=False, unique=True)

    # Имена файлов внутри DOCUMENTS_DIR/{order_id}/
    docx_key: Mapped[str] = mapped_column(String, nullable=False)
    pdf_key: Mapped[str] = mapped_column(String, nullable=False)
    instruction_pdf_key: Mapped[str | None] = mapped_column(String, nullable=True)
    user_encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship("Order", back_populates="document")  # noqa: F821
