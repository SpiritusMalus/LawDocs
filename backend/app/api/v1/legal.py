"""Публичная выдача канонического текста оферты.

Единственный источник текста оферты — `app/legal/offer/<version>.md` (его же
хэширует app/core/consent.py и штампует на заказ). Фронт рендерит /legal/offer
из этого эндпоинта, поэтому показанный текст и захэшированный не могут разойтись.
"""

from fastapi import APIRouter

from app.core.consent import (
    CONSENT_DATE_HUMAN,
    CONSENT_TEXT,
    CONSENT_TEXT_HASH,
    CONSENT_VERSION,
)
from app.schemas.legal import OfferOut

router = APIRouter()


@router.get("/offer", response_model=OfferOut)
async def get_offer() -> OfferOut:
    """Действующая редакция оферты: версия, дата, канонический текст и его SHA-256."""
    return OfferOut(
        version=CONSENT_VERSION,
        edition_human=CONSENT_DATE_HUMAN,
        text_hash=CONSENT_TEXT_HASH,
        text=CONSENT_TEXT,
    )
