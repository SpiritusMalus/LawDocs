import html
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.order import Order
from app.models.review import OrderReview
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def require_admin(x_admin_secret: str | None = Header(default=None)) -> None:
    if not settings.ADMIN_SECRET or x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


class ReviewCreate(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=50, max_length=1000)
    name: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=50)

    @field_validator("text", "name", "city", mode="before")
    @classmethod
    def strip_and_escape(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = str(v).strip()
        return html.escape(stripped) if stripped else None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rating: int
    text: str
    name: str | None
    city: str | None
    completed_orders_count: int
    created_at: datetime
    situation_id: str


class AdminReviewOut(ReviewOut):
    is_hidden: bool
    order_id: str
    user_id: str


class ReviewListOut(BaseModel):
    reviews: list[ReviewOut]
    total: int
    page: int


@router.post("/", response_model=ReviewOut, status_code=201)
async def create_review(
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderReview:
    result = await db.execute(select(Order).where(Order.id == body.order_id))
    order = result.scalar_one_or_none()
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Заказ не найден или не принадлежит вам.")
    if order.status != "done":
        raise HTTPException(status_code=400, detail="Отзыв можно оставить только после успешного завершения заказа.")

    existing = await db.execute(
        select(OrderReview).where(OrderReview.order_id == body.order_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Отзыв на этот заказ уже оставлен.")

    review = OrderReview(
        order_id=body.order_id,
        user_id=current_user.id,
        situation_id=order.situation_id,
        rating=body.rating,
        text=body.text,
        name=body.name,
        city=body.city,
        completed_orders_count=current_user.completed_orders_count,
    )
    db.add(review)

    # Сохраняем имя в профиль при первом отзыве
    if body.name and not current_user.name:
        current_user.name = body.name

    await db.commit()
    await db.refresh(review)
    return review


@router.get("/my", response_model=ReviewOut | None)
async def get_my_review(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderReview | None:
    result = await db.execute(
        select(OrderReview).where(
            OrderReview.order_id == order_id,
            OrderReview.user_id == current_user.id,
        )
    )
    return result.scalar_one_or_none()


@router.get("/", response_model=ReviewListOut)
async def list_reviews(
    page: int = 1,
    limit: int = 10,
    situation: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ReviewListOut:
    limit = min(max(limit, 1), 50)
    offset = (page - 1) * limit

    base = select(OrderReview).where(OrderReview.is_hidden.is_(False))
    count_base = select(func.count()).select_from(OrderReview).where(OrderReview.is_hidden.is_(False))

    if situation:
        base = base.where(OrderReview.situation_id == situation)
        count_base = count_base.where(OrderReview.situation_id == situation)

    base = base.order_by(OrderReview.created_at.desc()).offset(offset).limit(limit)

    reviews = (await db.execute(base)).scalars().all()
    total = (await db.execute(count_base)).scalar_one()

    return ReviewListOut(reviews=list(reviews), total=total, page=page)


@router.get("/admin", response_model=list[AdminReviewOut])
async def list_all_reviews_admin(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[OrderReview]:
    result = await db.execute(
        select(OrderReview).order_by(OrderReview.created_at.desc())
    )
    return list(result.scalars().all())


@router.patch("/{review_id}/visibility", response_model=AdminReviewOut)
async def toggle_review_visibility(
    review_id: str,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrderReview:
    result = await db.execute(select(OrderReview).where(OrderReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.is_hidden = not review.is_hidden
    await db.commit()
    await db.refresh(review)
    return review
