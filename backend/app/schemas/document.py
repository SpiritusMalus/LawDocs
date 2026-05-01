from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    order_id: str
    docx_url: str
    pdf_url: str
    generated_at: datetime

    model_config = {"from_attributes": True}
