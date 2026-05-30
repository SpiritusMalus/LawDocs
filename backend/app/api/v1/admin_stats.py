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


class AdminStatsOut(BaseModel):
    period: Period
    orders_total: int          # все не-draft заказы за период
    orders_paid: int           # с подтверждённой оплатой (paid_at)
    revenue_kopecks: int       # сумма amount по оплаченным
    conversion_pct: float      # orders_paid / orders_total * 100
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
        stmt = stmt.where(Order.status != "draft")
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
        .where(Order.status.in_(["failed", "refunded"]))
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
        by_status=by_status,
        by_situation=by_situation,
        problem_orders=problem_orders,
    )
