"""Версия пользовательского согласия (оферта + обработка ПДн).

Единый источник версии на бэкенде. Та же редакция продублирована на фронте в
`frontend/lib/legal-version.ts` (OFFER_EDITION) и показывается на /legal/offer.
Инвариант-тест `tests/test_consent_version.py` следит, чтобы значения не
разошлись: рассинхрон версии/даты бьёт по юр-доказуемости акцепта.

При изменении текста оферты — поднимать ОБА значения (здесь и в legal-version.ts).
Версию проставляет сервер (не доверяем фронту).
"""

from hashlib import sha256
from pathlib import Path

CONSENT_VERSION = "2026-06-02"
# Человекочитаемая дата редакции — зеркало OFFER_EDITION.human на фронте.
CONSENT_DATE_HUMAN = "2 июня 2026 г."

# Канонический текст оферты — единственный источник. Бэкенд хэширует его и штампует
# хэш на заказ (доказуемость акцепта: видно не только «версию», а контент редакции).
# Фронт рендерит этот же текст через GET /api/v1/legal/offer → drift невозможен.
_OFFER_DIR = Path(__file__).resolve().parents[1] / "legal" / "offer"


def _normalize(text: str) -> str:
    """Канонизируем перед хэшем: \\r\\n → \\n, без хвостовых пробелов и финальных пустых строк.

    Иначе хэш зависел бы от настроек редактора (CRLF, trailing newline) — нестабильно.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip()


def load_offer_text(version: str = CONSENT_VERSION) -> str:
    """Канонический текст оферты для редакции version (нормализованный)."""
    return _normalize((_OFFER_DIR / f"{version}.md").read_text(encoding="utf-8"))


# Текст и его SHA-256 фиксируются на старте процесса (редакция неизменна в рамках версии).
CONSENT_TEXT = load_offer_text()
CONSENT_TEXT_HASH = sha256(CONSENT_TEXT.encode("utf-8")).hexdigest()
