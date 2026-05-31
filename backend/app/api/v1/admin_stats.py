"""Админ-дашборд: агрегированные бизнес-метрики по заказам.

Защищён тем же admin-токеном, что и админ-эндпоинты отзывов (require_admin).
Отдаёт только агрегаты и обезличенные поля заказа (без form_data / ПДн).
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.enums import OrderStatus
from app.models.order import Order

router = APIRouter()

Period = Literal["day", "week", "month", "all"]

_PERIOD_DELTAS: dict[str, timedelta | None] = {
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "all": None,
}


class ProblemOrder(BaseModel):
    id: str
    situation_id: str
    status: str
    amount: int
    created_at: datetime


class SituationCount(BaseModel):
    situation_id: str
    count: int


class FunnelOut(BaseModel):
    """Воронка по заказам. Начинается с «создан» — в БД нет шагов до отправки
    формы (заходы на сайт, брошенный wizard); их видит только Я.Метрика."""
    created: int     # = orders_total (форма отправлена, заказ создан)
    paid: int        # = orders_paid (оплачен)
    completed: int   # документ сгенерирован (status = done)


class AdminStatsOut(BaseModel):
    period: Period
    orders_total: int          # все не-draft заказы за период
    orders_paid: int           # с подтверждённой оплатой (paid_at)
    revenue_kopecks: int       # сумма amount по оплаченным
    conversion_pct: float      # orders_paid / orders_total * 100
    funnel: FunnelOut
    avg_create_to_pay_seconds: float | None  # среднее paid_at − created_at; None если нет оплат
    by_status: dict[str, int]
    by_situation: list[SituationCount]
    problem_orders: list[ProblemOrder]


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(
    period: Period = Query(default="week"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
) -> AdminStatsOut:
    delta = _PERIOD_DELTAS[period]
    cutoff = datetime.now(UTC) - delta if delta else None

    def _scoped(stmt):
        """Фильтр по периоду + исключаем черновики (не дошли до оплаты)."""
        stmt = stmt.where(Order.status != OrderStatus.DRAFT.value)
        if cutoff is not None:
            stmt = stmt.where(Order.created_at >= cutoff)
        return stmt

    orders_total = await db.scalar(_scoped(select(func.count(Order.id)))) or 0

    orders_paid = await db.scalar(
        _scoped(select(func.count(Order.id))).where(Order.paid_at.is_not(None))
    ) or 0

    revenue_kopecks = await db.scalar(
        _scoped(select(func.coalesce(func.sum(Order.amount), 0))).where(
            Order.paid_at.is_not(None)
        )
    ) or 0

    conversion_pct = round(orders_paid / orders_total * 100, 1) if orders_total else 0.0

    # Среднее время от создания заказа до оплаты (сек). NULL → None при нуле оплат.
    avg_create_to_pay_seconds = await db.scalar(
        _scoped(
            select(func.avg(func.extract("epoch", Order.paid_at - Order.created_at)))
        ).where(Order.paid_at.is_not(None))
    )
    avg_create_to_pay_seconds = (
        round(float(avg_create_to_pay_seconds), 1)
        if avg_create_to_pay_seconds is not None
        else None
    )

    status_rows = await db.execute(
        _scoped(select(Order.status, func.count(Order.id))).group_by(Order.status)
    )
    by_status = {status: count for status, count in status_rows.all()}

    situation_rows = await db.execute(
        _scoped(select(Order.situation_id, func.count(Order.id)))
        .group_by(Order.situation_id)
        .order_by(func.count(Order.id).desc())
    )
    by_situation = [
        SituationCount(situation_id=sid, count=count) for sid, count in situation_rows.all()
    ]

    problem_rows = await db.execute(
        _scoped(
            select(Order.id, Order.situation_id, Order.status, Order.amount, Order.created_at)
        )
        .where(Order.status.in_([OrderStatus.FAILED.value, OrderStatus.REFUNDED.value]))
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    problem_orders = [
        ProblemOrder(
            id=row.id,
            situation_id=row.situation_id,
            status=row.status,
            amount=row.amount,
            created_at=row.created_at,
        )
        for row in problem_rows.all()
    ]

    return AdminStatsOut(
        period=period,
        orders_total=orders_total,
        orders_paid=orders_paid,
        revenue_kopecks=int(revenue_kopecks),
        conversion_pct=conversion_pct,
        funnel=FunnelOut(
            created=orders_total,
            paid=orders_paid,
            completed=by_status.get(OrderStatus.DONE.value, 0),
        ),
        avg_create_to_pay_seconds=avg_create_to_pay_seconds,
        by_status=by_status,
        by_situation=by_situation,
        problem_orders=problem_orders,
    )
