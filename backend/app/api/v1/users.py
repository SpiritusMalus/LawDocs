import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.validators import strip_whitespace
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class UserMeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None
    completed_orders_count: int
    public_key: str | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def validate_strip(cls, v: str | None) -> str | None:
        return strip_whitespace(v)


@router.get("/me", response_model=UserMeOut)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserMeOut)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    old_name = current_user.name
    current_user.name = body.name
    await db.commit()
    await db.refresh(current_user)
    if old_name != current_user.name:
        logger.info(f"User {current_user.id} updated name: {old_name!r} → {current_user.name!r}")
    return current_user
