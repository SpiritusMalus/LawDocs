from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


VALID_SITUATIONS = {
    "shop", "marketplace", "bank", "employer",
    "insurance", "utility", "airline", "other",
}


def _validate_situation(value: str) -> str:
    if value not in VALID_SITUATIONS:
        raise ValueError(f"Unknown situation_id: {value}")
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
    def check_form_data_size(cls, v: dict) -> dict:
        import json
        if len(json.dumps(v, ensure_ascii=False)) > 32_000:
            raise ValueError("form_data too large (max 32 KB)")
        return v


class OrderInitOut(BaseModel):
    order_id: str


class OrderCreate(BaseModel):
    situation_id: str
    form_data: dict

    @field_validator("situation_id")
    @classmethod
    def check_situation(cls, v: str) -> str:
        return _validate_situation(v)


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
