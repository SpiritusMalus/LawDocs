from typing import Annotated

from pydantic import AfterValidator, EmailStr


def strip_whitespace(v: str | None) -> str | None:
    if v is None:
        return v
    stripped = str(v).strip()
    return stripped if stripped else None


# Запрет на Gmail для регистрации в РФ. googlemail.com — историческое зеркало
# Gmail, письма ведут в тот же ящик, поэтому блокируем оба домена.
GMAIL_BLOCKED_MESSAGE = "Извините, gmail запрещен в России для регистрации"
_BLOCKED_EMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})


def reject_blocked_email(value: str) -> str:
    """Отклоняет почту на запрещённых доменах (Gmail и его зеркало)."""
    domain = value.rsplit("@", 1)[-1].lower()
    if domain in _BLOCKED_EMAIL_DOMAINS:
        raise ValueError(GMAIL_BLOCKED_MESSAGE)
    return value


# EmailStr проверяет формат, затем AfterValidator отсекает запрещённые домены.
# Используется вместо EmailStr во всех схемах, где человек вводит почту.
Email = Annotated[EmailStr, AfterValidator(reject_blocked_email)]
