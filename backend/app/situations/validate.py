"""Серверная валидация дат в form_data по декларативным правилам WizardField.

Правила (`not_future`, `min_field`, `max_field`) живут рядом с полем в YAML —
один источник правды и для фронта (мгновенная проверка), и для сервера (защита
API). Здесь — серверная половина: пробегаем по date-полям ситуации и сверяем
формат и логические связи дат. Сравнение значений идёт через алиасы полей
(`field_resolve`), т.к. контактные/шапочные поля встречаются под разными именами.
"""

from __future__ import annotations

from datetime import date, datetime

from app.services.field_resolve import resolve_field_value
from app.situations.models import SituationConfig, WizardField

# Те же форматы, что принимает калькулятор (_parse_date): фронт шлёт «дд.мм.гггг»,
# исторические/тестовые данные — ISO. Держим список здесь, чтобы валидация и
# расчёт не разъезжались.
_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")


def _parse(value: str | None) -> date | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def validate_lengths(config: SituationConfig, form_data: dict) -> None:
    """Проверяет лимит длины (`max_len`) для полей ситуации. По выбору пользователя
    контролируем только длину, без проверки символов. Бросает ValueError при
    первом превышении.
    """
    for step in config.wizard_steps:
        for field in step.fields:
            if field.max_len is None:
                continue
            value = form_data.get(field.id)
            if isinstance(value, str) and len(value) > field.max_len:
                raise ValueError(
                    f"Поле «{field.label}»: не более {field.max_len} символов."
                )


def _date_fields(config: SituationConfig) -> list[WizardField]:
    return [
        field
        for step in config.wizard_steps
        for field in step.fields
        if field.type == "date"
    ]


def _value_for(field_id: str, form_data: dict) -> str:
    """Значение поля с учётом алиасов; для cross-field сравнений."""
    direct = form_data.get(field_id)
    if direct:
        return str(direct)
    return resolve_field_value(field_id, form_data)


def validate_dates(config: SituationConfig, form_data: dict) -> None:
    """Бросает ValueError с человекочитаемым сообщением при первой ошибке.

    Пустые необязательные даты пропускаются (требование `required` проверяется
    отдельно). Невалидный формат и логические противоречия — ошибка.
    """
    fields = _date_fields(config)
    by_id = {f.id: f for f in fields}
    today = date.today()

    for field in fields:
        raw = _value_for(field.id, form_data)
        if not raw:
            continue  # пустое необязательное поле — не наша забота

        parsed = _parse(raw)
        if parsed is None:
            raise ValueError(f"Поле «{field.label}»: неверная дата. Формат — дд.мм.гггг.")

        if field.not_future and parsed > today:
            raise ValueError(f"Поле «{field.label}»: дата не может быть в будущем.")

        if field.min_field:
            other = _parse(_value_for(field.min_field, form_data))
            if other and parsed < other:
                other_label = by_id[field.min_field].label if field.min_field in by_id else field.min_field
                raise ValueError(
                    f"Поле «{field.label}» не может быть раньше, чем «{other_label}»."
                )

        if field.max_field:
            other = _parse(_value_for(field.max_field, form_data))
            if other and parsed > other:
                other_label = by_id[field.max_field].label if field.max_field in by_id else field.max_field
                raise ValueError(
                    f"Поле «{field.label}» не может быть позже, чем «{other_label}»."
                )
