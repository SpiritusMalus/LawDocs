"""Тесты OrderStatus enum и валидации формата документа (рефакторинг Фаз 1-3)."""
import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import validate_format
from app.core.enums import OrderStatus
from app.models.order import Order
from app.models.user import User


def test_order_status_values_match_contract():
    # Значения enum должны совпадать с фронтовым типом OrderStatus (api-schemas.ts).
    assert {s.value for s in OrderStatus} == {
        "draft", "pending_payment", "paid", "generating", "done", "failed", "refunded",
    }


def test_order_status_is_str_compatible():
    # str-наследование: enum сравнивается со строкой и сериализуется как строка,
    # поэтому колонка БD остаётся String и фронт получает обычную строку.
    assert OrderStatus.REFUNDED == "refunded"
    assert OrderStatus.REFUNDED.value == "refunded"


def test_validate_format_accepts_docx_pdf():
    assert validate_format("docx") == "docx"
    assert validate_format("pdf") == "pdf"


def test_validate_format_rejects_other():
    for bad in ("exe", "txt", "", "PDF"):
        with pytest.raises(HTTPException) as exc:
            validate_format(bad)
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_refunded_order_serializes_status_as_string(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    # Заказ в статусе refunded должен отдаваться API как строка "refunded" —
    # на это завязан экран возврата на фронте (order-status.tsx).
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data={},
        status=OrderStatus.REFUNDED.value,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"
