"""Tests for run_document_generation — the background generation task.

Heavy I/O (LLM, docgen, storage, email, telegram) is mocked; the DB layer
is real (test container) via AsyncSessionLocal patched to the test factory.
Pins the happy-path and failure-path contracts after decomposition.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus
from app.models.document import Document
from app.models.order import Order
from app.models.user import User
from app.services import generation

from tests.conftest import _TestSessionLocal

FORM_DATA = {"seller_name": "ООО Ромашка", "problem_type": "defect"}


async def _make_order(db_session: AsyncSession, user: User, **overrides) -> Order:
    defaults = dict(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status=OrderStatus.GENERATING.value,
        amount=19900,
    )
    defaults.update(overrides)
    order = Order(**defaults)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.mark.asyncio
async def test_generation_success_marks_done_and_creates_document(
    db_session: AsyncSession, user: User
):
    order = await _make_order(db_session, user)

    with (
        patch.object(generation, "AsyncSessionLocal", _TestSessionLocal),
        patch("app.services.llm.fill_template", new=AsyncMock(return_value=("body", ["hdr"], "ПРЕТЕНЗИЯ"))),
        patch("app.services.docgen.generate_document", new=AsyncMock(return_value=("docx_key", "pdf_key"))),
        patch.object(generation, "_generate_instruction", new=AsyncMock(return_value="instr_key")),
        patch("app.services.email.send_document_ready", new=AsyncMock()) as mock_email,
    ):
        await generation.run_document_generation(
            order_id=order.id,
            situation_id="shop",
            form_data=FORM_DATA,
            user_email="test@example.com",
        )

    await db_session.refresh(order)
    assert order.status == OrderStatus.DONE.value
    assert order.payment_url is None
    assert order.form_data == {}  # ПДн стёрты после доставки письма
    mock_email.assert_awaited_once()

    doc = (await db_session.execute(select(Document).where(Document.order_id == order.id))).scalar_one()
    assert doc.docx_key == "docx_key"
    assert doc.pdf_key == "pdf_key"
    assert doc.instruction_pdf_key == "instr_key"
    assert doc.user_encrypted is False


@pytest.mark.asyncio
async def test_generation_failure_refunds_when_paid(db_session: AsyncSession, user: User):
    order = await _make_order(db_session, user, yookassa_payment_id="pay_123")

    with (
        patch.object(generation, "AsyncSessionLocal", _TestSessionLocal),
        patch("app.services.llm.fill_template", new=AsyncMock(side_effect=RuntimeError("LLM down"))),
        patch("app.services.payment.refund_payment", new=AsyncMock(return_value=True)) as mock_refund,
        patch("app.services.email.send_refund_notification", new=AsyncMock()) as mock_refund_email,
        patch("app.services.notifications.send_telegram_alert", new=AsyncMock()),
    ):
        await generation.run_document_generation(
            order_id=order.id,
            situation_id="shop",
            form_data=FORM_DATA,
            user_email="test@example.com",
        )

    await db_session.refresh(order)
    assert order.status == OrderStatus.REFUNDED.value
    assert order.form_data == {}
    mock_refund.assert_awaited_once_with("pay_123", 19900)
    mock_refund_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_failure_marks_failed_when_no_payment(db_session: AsyncSession, user: User):
    order = await _make_order(db_session, user, yookassa_payment_id=None)

    with (
        patch.object(generation, "AsyncSessionLocal", _TestSessionLocal),
        patch("app.services.llm.fill_template", new=AsyncMock(side_effect=RuntimeError("LLM down"))),
        patch("app.services.email.send_document_failed", new=AsyncMock()) as mock_failed_email,
        patch("app.services.notifications.send_telegram_alert", new=AsyncMock()),
    ):
        await generation.run_document_generation(
            order_id=order.id,
            situation_id="shop",
            form_data=FORM_DATA,
            user_email="test@example.com",
        )

    await db_session.refresh(order)
    assert order.status == OrderStatus.FAILED.value
    mock_failed_email.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_no_notify_marks_failed_without_refund(db_session: AsyncSession, user: User):
    """notify_on_failure=False (auto-retry loop): no refund, no notification."""
    order = await _make_order(db_session, user, yookassa_payment_id="pay_123")

    with (
        patch.object(generation, "AsyncSessionLocal", _TestSessionLocal),
        patch("app.services.llm.fill_template", new=AsyncMock(side_effect=RuntimeError("LLM down"))),
        patch("app.services.payment.refund_payment", new=AsyncMock()) as mock_refund,
    ):
        await generation.run_document_generation(
            order_id=order.id,
            situation_id="shop",
            form_data=FORM_DATA,
            user_email="test@example.com",
            notify_on_failure=False,
        )

    await db_session.refresh(order)
    assert order.status == OrderStatus.FAILED.value
    mock_refund.assert_not_awaited()


@pytest.mark.asyncio
async def test_generation_missing_order_is_noop(db_session: AsyncSession):
    """Unknown order_id returns silently without raising."""
    with patch.object(generation, "AsyncSessionLocal", _TestSessionLocal):
        await generation.run_document_generation(
            order_id="00000000-0000-0000-0000-000000000099",
            situation_id="shop",
            form_data=FORM_DATA,
            user_email="test@example.com",
        )
