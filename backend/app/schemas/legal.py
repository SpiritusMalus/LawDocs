from pydantic import BaseModel


class OfferOut(BaseModel):
    """Действующая редакция оферты для публичного рендера и доказуемости акцепта."""

    version: str  # машинная версия редакции (= offer_version на заказе)
    edition_human: str  # человекочитаемая дата редакции
    text_hash: str  # SHA-256 канонического текста (= offer_text_hash на заказе)
    text: str  # канонический текст оферты (markdown)
