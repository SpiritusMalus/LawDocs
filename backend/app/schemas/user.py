from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}
