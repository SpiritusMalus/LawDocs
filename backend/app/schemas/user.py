from pydantic import BaseModel

from app.core.validators import Email


class MagicLinkRequest(BaseModel):
    email: Email


class UserOut(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}
