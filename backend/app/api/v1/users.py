import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.validators import strip_whitespace
from app.models.document import Document
from app.models.order import Order
from app.models.review import OrderReview
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


class OrderExport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    situation_id: str
    status: str
    amount: int
    created_at: datetime
    paid_at: datetime | None = None


class DataExport(BaseModel):
    exported_at: datetime
    user: dict
    orders: list[OrderExport]


@router.get("/me/data-export", response_model=DataExport)
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DataExport:
    orders_result = await db.execute(select(Order).where(Order.user_id == current_user.id))
    orders = orders_result.scalars().all()
    return DataExport(
        exported_at=datetime.now(timezone.utc),
        user={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "consent_version": current_user.consent_version,
            "consent_timestamp": current_user.consent_timestamp.isoformat() if current_user.consent_timestamp else None,
        },
        orders=list(orders),
    )


class ProcessingRestrictionOut(BaseModel):
    processing_restricted: bool
    processing_restricted_at: datetime | None = None


@router.post("/me/restrict-processing", response_model=ProcessingRestrictionOut)
async def restrict_processing(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingRestrictionOut:
    now = datetime.now(timezone.utc)
    current_user.processing_restricted = True
    current_user.processing_restricted_at = now
    await db.commit()
    logger.info(f"User {current_user.id} restricted data processing")
    return ProcessingRestrictionOut(processing_restricted=True, processing_restricted_at=now)


@router.delete("/me/restrict-processing", response_model=ProcessingRestrictionOut)
async def unrestrict_processing(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessingRestrictionOut:
    current_user.processing_restricted = False
    current_user.processing_restricted_at = None
    await db.commit()
    logger.info(f"User {current_user.id} lifted data processing restriction")
    return ProcessingRestrictionOut(processing_restricted=False, processing_restricted_at=None)


@router.delete("/me", status_code=204)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    user_id = current_user.id
    # anonymize reviews so public testimonials remain intact
    await db.execute(update(OrderReview).where(OrderReview.user_id == user_id).values(user_id=None, name=None))
    # delete documents and orders
    orders_result = await db.execute(select(Order).where(Order.user_id == user_id))
    for order in orders_result.scalars().all():
        doc_result = await db.execute(select(Document).where(Document.order_id == order.id))
        doc = doc_result.scalar_one_or_none()
        if doc:
            await db.delete(doc)
        await db.delete(order)
    await db.delete(current_user)
    await db.commit()
    logger.info(f"User {user_id} deleted their account")
    return Response(status_code=204)
