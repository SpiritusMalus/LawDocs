from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


class UserMeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None
    completed_orders_count: int


@router.get("/me", response_model=UserMeOut)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
