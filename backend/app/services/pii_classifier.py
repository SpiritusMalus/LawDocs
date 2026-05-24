"""
Классификация полей form_data для границы приватности.

Назначение: определить, какие поля можно отдавать во внешнюю LLM (GigaChat),
а какие содержат персональные данные и наружу уходить не должны.

Главный принцип безопасности — **deny by default**: всё, что явно не отнесено
к TEXT или ROUTING, считается SENSITIVE и в LLM не отправляется. Новое поле,
добавленное в YAML-ситуацию и забытое здесь, по умолчанию защищено, а не утекает.

Поэтому здесь НЕТ эвристик по именам в «разрешающую» сторону: разрешено только
то, что перечислено явно.

Списки — подтверждены пользователем (handoff_62 разд.4, решение I), без изменений.
"""

from __future__ import annotations

from enum import Enum


class FieldClass(str, Enum):
    """Класс поля form_data относительно границы приватности."""

    SENSITIVE = "sensitive"  # ПДн — НЕ отправлять в LLM, шифровать at-rest
    TEXT = "text"            # свободный нарратив без идентификаторов — можно в LLM
    ROUTING = "routing"      # коды/перечисления для выбора шаблона — можно в LLM


# TEXT — свободные описания ситуации, которые LLM перефразирует (handoff_62 разд.4):
TEXT_FIELDS: frozenset[str] = frozenset({
    "problem_desc",
    "store_response",
    "additional_desc",
    "incident_desc",
    "demand",
})

# ROUTING — перечисления/коды для выбора шаблона и норм, не ПДн (handoff_62 разд.4):
ROUTING_FIELDS: frozenset[str] = frozenset({
    "situation_id",
    "problem_type",
    "violation_type",
    "incident_type",
    "platform",
    "platform_other",
    "policy_type",
    "reason",          # gym_refund: причина отказа (club_closed/terms_changed/medical/voluntary)
})


def classify_field(field_id: str) -> FieldClass:
    """Возвращает класс поля. Неизвестное поле → SENSITIVE (deny by default)."""
    if field_id in TEXT_FIELDS:
        return FieldClass.TEXT
    if field_id in ROUTING_FIELDS:
        return FieldClass.ROUTING
    return FieldClass.SENSITIVE


def is_safe_for_llm(field_id: str) -> bool:
    """True, если поле можно отправлять во внешнюю LLM (TEXT или ROUTING)."""
    return classify_field(field_id) in (FieldClass.TEXT, FieldClass.ROUTING)


def split_for_llm(form_data: dict) -> tuple[dict, dict]:
    """Делит form_data на (safe_for_llm, sensitive).

    safe_for_llm — TEXT/ROUTING поля, допустимые в промпте GigaChat.
    sensitive — ПДн, подставляются в документ локально (плейсхолдеры/калькуляторы).
    """
    safe: dict = {}
    sensitive: dict = {}
    for key, value in form_data.items():
        if is_safe_for_llm(key):
            safe[key] = value
        else:
            sensitive[key] = value
    return safe, sensitive
