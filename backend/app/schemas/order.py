import json
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

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

        from app.situations.registry import registry
        allowed = registry.all_field_ids()
        if allowed:  # пропускаем если registry ещё не загружен (тесты)
            unknown = set(v.keys()) - allowed
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
    requires_verification: bool = True
    redirect_to: str | None = None


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
    payment_url: str | None = None

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: str
    situation_id: str
    status: str
    amount: int
    created_at: datetime
    has_document: bool = False

    model_config = {"from_attributes": True}
