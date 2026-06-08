"""Инвариант: версия/дата оферты на бэкенде и на фронте не должны расходиться.

Бэкенд штампует CONSENT_VERSION на заказ как доказательство принятой редакции,
а фронт показывает дату из frontend/lib/legal-version.ts. Если их рассинхронить
при обновлении оферты — по заказу будет одна версия, а пользователь видел другую
дату. Этот тест ловит расхождение в CI.
"""
import re
from hashlib import sha256
from pathlib import Path

from app.core.consent import (
    CONSENT_DATE_HUMAN,
    CONSENT_TEXT,
    CONSENT_TEXT_HASH,
    CONSENT_VERSION,
    load_offer_text,
)

_LEGAL_VERSION_TS = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "legal-version.ts"


def _extract(field: str, source: str) -> str:
    m = re.search(rf'{field}:\s*"([^"]+)"', source)
    assert m, f"Не нашёл поле {field} в legal-version.ts"
    return m.group(1)


def test_offer_version_matches_frontend():
    assert _LEGAL_VERSION_TS.exists(), f"Нет файла {_LEGAL_VERSION_TS}"
    source = _LEGAL_VERSION_TS.read_text(encoding="utf-8")

    assert _extract("version", source) == CONSENT_VERSION
    assert _extract("human", source) == CONSENT_DATE_HUMAN


def test_consent_version_is_iso_date():
    """CONSENT_VERSION — дата в формате YYYY-MM-DD (машинно сравнимая редакция)."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", CONSENT_VERSION)


def test_canonical_offer_file_exists_for_version():
    """Для действующей CONSENT_VERSION есть канонический текст оферты на диске."""
    offer_file = Path(__file__).resolve().parents[1] / "app" / "legal" / "offer" / f"{CONSENT_VERSION}.md"
    assert offer_file.exists(), f"Нет канонического текста оферты {offer_file}"
    assert load_offer_text(CONSENT_VERSION).strip(), "Канонический текст оферты пуст"


def test_offer_text_hash_matches_canonical_text():
    """offer_text_hash, который штампуется на заказ, = SHA-256 канонического текста.

    Ловит рассинхрон, если кто-то поправит текст оферты, но забудет, что хэш
    пересчитывается из файла (иначе на заказах был бы хэш «не того» текста)."""
    assert CONSENT_TEXT_HASH == sha256(CONSENT_TEXT.encode("utf-8")).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", CONSENT_TEXT_HASH)
