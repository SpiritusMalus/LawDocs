"""Тесты админ-дашборда метрик (GET /api/v1/admin/stats)."""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import User


async def _seed_orders(db: AsyncSession, user: User) -> None:
    now = datetime.now(UTC)
    orders = [
        # оплаченные done
        Order(user_id=user.id, situation_id="shop", status="done", amount=19900,
              paid_at=now, created_at=now),
        Order(user_id=user.id, situation_id="shop", status="done", amount=19900,
              paid_at=now, created_at=now),
        # оплачен, но упал
        Order(user_id=user.id, situation_id="bank", status="failed", amount=19900,
              paid_at=now, created_at=now),
        # возврат
        Order(user_id=user.id, situation_id="mfo", status="refunded", amount=19900,
              paid_at=now, created_at=now),
        # не оплачен (создан, ждёт оплаты) — в total входит, в paid нет
        Order(user_id=user.id, situation_id="shop", status="pending_payment", amount=19900,
              created_at=now),
        # черновик — НЕ должен учитываться вообще
        Order(user_id=user.id, situation_id="shop", status="draft", amount=19900,
              created_at=now),
        # старый заказ (вне периода day/week) — попадёт только в all
        Order(user_id=user.id, situation_id="shop", status="done", amount=19900,
              paid_at=now - timedelta(days=60), created_at=now - timedelta(days=60)),
    ]
    for o in orders:
        db.add(o)
    await db.commit()


@pytest.mark.asyncio
async def test_admin_stats_requires_token(client: AsyncClient):
    resp = await client.get("/api/v1/admin/stats")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_week_aggregates(
    client: AsyncClient, db_session: AsyncSession, user: User, admin_token: str
):
    await _seed_orders(db_session, user)

    resp = await client.get(
        "/api/v1/admin/stats?period=week",
        headers={"X-Admin-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()

    # За неделю: 5 не-draft (draft и 60-дневный исключены)
    assert data["orders_total"] == 5
    # Оплачено (paid_at): 2 done + 1 failed + 1 refunded = 4
    assert data["orders_paid"] == 4
    assert data["revenue_kopecks"] == 4 * 19900
    assert data["conversion_pct"] == 80.0  # 4/5

    assert data["by_status"]["done"] == 2
    assert data["by_status"]["failed"] == 1
    assert data["by_status"]["refunded"] == 1
    assert "draft" not in data["by_status"]

    # shop — самая частая ситуация за неделю (2 done + 1 pending = 3)
    assert data["by_situation"][0]["situation_id"] == "shop"
    assert data["by_situation"][0]["count"] == 3

    # проблемные: failed + refunded = 2, без form_data в ответе
    assert len(data["problem_orders"]) == 2
    statuses = {o["status"] for o in data["problem_orders"]}
    assert statuses == {"failed", "refunded"}
    assert "form_data" not in data["problem_orders"][0]


@pytest.mark.asyncio
async def test_admin_stats_funnel(
    client: AsyncClient, db_session: AsyncSession, user: User, admin_token: str
):
    await _seed_orders(db_session, user)

    resp = await client.get(
        "/api/v1/admin/stats?period=week",
        headers={"X-Admin-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()

    funnel = data["funnel"]
    assert funnel["created"] == data["orders_total"]   # 5
    assert funnel["paid"] == data["orders_paid"]        # 4
    assert funnel["completed"] == 2                      # два done за неделю

    # В сиде paid_at == created_at → среднее время ≈ 0, но НЕ None (оплаты есть).
    assert data["avg_create_to_pay_seconds"] is not None
    assert data["avg_create_to_pay_seconds"] == pytest.approx(0, abs=1)


@pytest.mark.asyncio
async def test_admin_stats_empty_funnel_no_division_by_zero(
    client: AsyncClient, db_session: AsyncSession, user: User, admin_token: str
):
    """Заказов нет (как на проде сейчас): 200 OK, пустая воронка, время None."""
    resp = await client.get(
        "/api/v1/admin/stats?period=week",
        headers={"X-Admin-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["orders_total"] == 0
    assert data["conversion_pct"] == 0.0
    assert data["funnel"] == {"created": 0, "paid": 0, "completed": 0}
    assert data["avg_create_to_pay_seconds"] is None


@pytest.mark.asyncio
async def test_admin_stats_all_includes_old(
    client: AsyncClient, db_session: AsyncSession, user: User, admin_token: str
):
    await _seed_orders(db_session, user)
    resp = await client.get(
        "/api/v1/admin/stats?period=all",
        headers={"X-Admin-Token": admin_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    # all: те же 5 + старый done = 6 не-draft
    assert data["orders_total"] == 6
    assert data["orders_paid"] == 5  # +старый оплаченный
