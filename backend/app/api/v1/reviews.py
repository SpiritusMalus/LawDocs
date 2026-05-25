import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import ALGORITHM
from app.core.validators import strip_whitespace
from app.models.order import Order
from app.models.review import OrderReview
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def create_admin_token() -> str:
    expire = datetime.now(UTC) + timedelta(hours=4)
    return jwt.encode(
        {"role": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        payload = jwt.decode(x_admin_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
    except JWTError:
        raise HTTPException(status_code=403, detail="Forbidden")


class ReviewCreate(BaseModel):
    order_id: str
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=50, max_length=1000)
    name: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=50)

    @field_validator("text", "name", "city", mode="before")
    @classmethod
    def validate_strip(cls, v: str | None) -> str | None:
        return strip_whitespace(v)


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


class AdminTokenOut(BaseModel):
    admin_token: str


@router.post("/admin/token", response_model=AdminTokenOut)
@limiter.limit("5/minute")
async def create_admin_session(
    request: Request,
    x_admin_secret: str | None = Header(default=None),
) -> AdminTokenOut:
    if not settings.ADMIN_SECRET or not secrets.compare_digest(
        x_admin_secret or "", settings.ADMIN_SECRET
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    return AdminTokenOut(admin_token=create_admin_token())


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

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "order_id" in str(e):
            raise HTTPException(status_code=409, detail="Отзыв на этот заказ уже оставлен.")
        raise

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
    page = max(page, 1)
    offset = (page - 1) * limit

    base = select(OrderReview).where(OrderReview.is_hidden.is_(False))
    count_base = select(func.count()).select_from(OrderReview).where(OrderReview.is_hidden.is_(False))

    if situation:
        base = base.where(OrderReview.situation_id == situation)
        count_base = count_base.where(OrderReview.situation_id == situation)

    base = base.order_by(OrderReview.created_at.desc()).offset(offset).limit(limit)

    reviews = (await db.execute(base)).scalars().all()
    total = (await db.execute(count_base)).scalar_one()

    return ReviewListOut(reviews=reviews, total=total, page=page)


@router.get("/admin", response_model=ReviewListOut)
async def list_all_reviews_admin(
    page: int = 1,
    limit: int = 100,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ReviewListOut:
    limit = min(max(limit, 1), 500)
    offset = (page - 1) * limit
    page = max(page, 1)

    base = select(OrderReview).order_by(OrderReview.created_at.desc())
    count_base = select(func.count()).select_from(OrderReview)

    result = await db.execute(base.offset(offset).limit(limit))
    reviews = result.scalars().all()
    total = (await db.execute(count_base)).scalar_one()

    return ReviewListOut(reviews=reviews, total=total, page=page)


@router.patch("/{review_id}/visibility", response_model=AdminReviewOut)
async def toggle_review_visibility(
    review_id: str,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrderReview:
    result = await db.execute(
        select(OrderReview)
        .where(OrderReview.id == review_id)
        .with_for_update()
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.is_hidden = not review.is_hidden
    await db.commit()
    await db.refresh(review)
    return review
