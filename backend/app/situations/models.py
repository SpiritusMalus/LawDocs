from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


class LegalRef(BaseModel):
    law: str
    url: str


class WizardFieldOption(BaseModel):
    value: str
    label: str


class WizardField(BaseModel):
    id: str
    type: Literal["text", "number", "date", "textarea", "radio"]
    label: str
    placeholder: str | None = None
    required: bool = False
    hint: str | None = None
    options: list[WizardFieldOption] | None = None

    # Декларативная валидация дат. Один источник правды: эти поля едут на фронт
    # (через SituationDetailOut) для мгновенной проверки и дублируются на сервере
    # (schemas/order.py) для защиты API.
    not_future: bool = False        # дата не может быть позже сегодняшней
    min_field: str | None = None    # id другого date-поля: это поле должно быть ≥ него
    max_field: str | None = None    # id другого date-поля: это поле должно быть ≤ него

    # Лимит длины значения (символов). Фронт ставит maxLength у input, сервер
    # проверяет повторно. Без проверки символов — только длина (решение пользователя).
    max_len: int | None = None


class WizardStep(BaseModel):
    title: str
    fields: list[WizardField]


class HeaderField(BaseModel):
    """Одна строка шапки документа. Строится детерминированно из form_data."""
    field: str                  # ключ в form_data
    label: str | None = None    # текст перед значением, напр. "Руководителю" / "От:"
    prefix: str | None = None   # короткий префикс вплотную к значению, напр. "тел. "


class SituationConfig(BaseModel):
    id: str
    category: str
    title: str
    blurb: str
    examples: str = ""
    document_type: str = "pretenziya"
    template_file: str | None = None
    system_prompt: str
    python_template: str | None = None
    narrative_prompt: str | None = None
    narrative_fields: list[str] = []
    wizard_steps: list[WizardStep]
    append_contact_step: bool = True
    legal_refs: list[LegalRef] = []
    legal_refs_by_branch: dict[str, list[LegalRef]] = {}
    header_fields: list[HeaderField] = []
