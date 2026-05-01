from datetime import datetime

from pydantic import BaseModel


VALID_SITUATIONS = {
    "shop", "marketplace", "bank", "employer",
    "insurance", "utility", "airline", "other",
}


class OrderCreate(BaseModel):
    situation_id: str
    form_data: dict

    def model_post_init(self, __context) -> None:
        if self.situation_id not in VALID_SITUATIONS:
            raise ValueError(f"Unknown situation_id: {self.situation_id}")


class PaymentOut(BaseModel):
    order_id: str
    payment_url: str  # ЮKassa confirmation URL


class OrderOut(BaseModel):
    id: str
    situation_id: str
    status: str
    amount: int
    created_at: datetime
    paid_at: datetime | None

    model_config = {"from_attributes": True}
