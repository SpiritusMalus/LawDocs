import json
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

# Полный список допустимых ключей формы (из lib/wizard-questions.ts).
# Только эти ключи принимаются в form_data — любой другой отклоняется.
_ALLOWED_FORM_FIELDS: frozenset[str] = frozenset({
    "full_name", "contact_address", "phone", "email",
    "demand", "problem_desc", "problem_type", "violation_type",
    "store_name", "store_address", "product_name", "product_price",
    "purchase_date", "appeal_date", "store_response", "penalty_start_date",
    "platform", "platform_other", "order_number", "order_amount", "order_date",
    "incident_date", "withheld_amount",
    "bank_name", "contract_number", "violation_date", "amount",
    "company_name", "company_inn", "director_name", "company_address",
    "position", "hire_date", "debt_amount", "debt_period",
    "last_payment_date", "additional_desc",
    "insurance_company", "policy_type", "policy_number",
    "incident_type", "incident_desc", "actual_damage", "paid_amount", "overdue_days",
    "apartment_address", "violation_period", "disputed_amount",
    "airline", "flight_number", "route", "flight_date",
    "delay_hours", "ticket_price", "extra_expenses", "received_compensation",
})

_MAX_FIELD_VALUE_LEN = 5_000


def _validate_situation(value: str) -> str:
    from app.situations.registry import registry
    valid_ids = registry.ids()
    # If registry not yet loaded (e.g. tests before startup), skip validation
    if valid_ids and value not in valid_ids:
        raise ValueError(f"Unknown situation_id: {value!r}")
    return value


class OrderInitRequest(BaseModel):
    email: EmailStr
    situation_id: str
    form_data: dict

    @field_validator("situation_id")
    @classmethod
    def check_situation(cls, v: str) -> str:
        return _validate_situation(v)

    @field_validator("form_data")
    @classmethod
    def check_form_data(cls, v: dict) -> dict:
        if len(json.dumps(v, ensure_ascii=False)) > 32_000:
            raise ValueError("form_data too large (max 32 KB)")

        unknown = set(v.keys()) - _ALLOWED_FORM_FIELDS
        if unknown:
            raise ValueError(f"Недопустимые поля формы: {', '.join(sorted(unknown))}")

        for key, val in v.items():
            if not isinstance(val, str):
                raise ValueError(f"Поле {key!r} должно быть строкой")
            if len(val) > _MAX_FIELD_VALUE_LEN:
                raise ValueError(f"Поле {key!r} превышает {_MAX_FIELD_VALUE_LEN} символов")

        return v


class OrderInitOut(BaseModel):
    order_id: str


class PaymentOut(BaseModel):
    order_id: str
    payment_url: str


class OrderOut(BaseModel):
    id: str
    situation_id: str
    status: str
    amount: int
    created_at: datetime
    paid_at: datetime | None

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: str
    situation_id: str
    status: str
    amount: int
    created_at: datetime
    has_document: bool = False

    model_config = {"from_attributes": True}
