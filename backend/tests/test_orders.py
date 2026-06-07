"""Integration tests for orders API."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import User


FORM_DATA = {
    "full_name": "Иванов Иван Иванович",
    "phone": "+79001234567",
    "email": "ivan@example.com",
    "address_city": "Москва",
    "address_street": "Пушкина",
    "address_house": "1",
    "store_name": "ТестМаркет",
    "store_address_city": "Москва",
    "store_address_street": "Тверская",
    "store_address_house": "1",
    "product_name": "Тестовый товар",
    "product_price": "5000",
    "purchase_date": "01.01.2025",
    "problem_desc": "Товар оказался бракованным",
    "problem_type": "defect",
    "demand": "refund",
}


@pytest.mark.asyncio
async def test_init_order_guest_returns_order_token_and_redirect(client: AsyncClient):
    """Гость идёт сразу к оплате: order_token + redirect, без magic-link-гейта.

    Magic-link всё ещё шлётся (best-effort, для входа в аккаунт), но больше не
    блокирует и не является обязательным шагом перед оплатой.
    """
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(
            "/api/v1/orders/init",
            json={
                "email": "ivan@example.com",
                "situation_id": "shop",
                "form_data": FORM_DATA,
                "offer_accepted": True,
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["requires_verification"] is False
    assert data["redirect_to"] == f"/orders/{data['order_id']}"
    assert isinstance(data["order_token"], str) and len(data["order_token"]) > 0
    mock_mail.assert_called_once()


@pytest.mark.asyncio
async def test_init_order_guest_survives_mail_failure(client: AsyncClient):
    """Сбой почты не должен блокировать гостевую покупку — доступ даёт order_token."""
    with patch(
        "app.api.v1.orders.send_magic_link",
        new_callable=AsyncMock,
        side_effect=RuntimeError("smtp down"),
    ):
        resp = await client.post(
            "/api/v1/orders/init",
            json={
                "email": "ivan@example.com",
                "situation_id": "shop",
                "form_data": FORM_DATA,
                "offer_accepted": True,
            },
        )
    assert resp.status_code == 201
    assert resp.json()["order_token"]


@pytest.mark.asyncio
async def test_init_order_authenticated_skips_magic_link(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={
                "email": "ivan@example.com",
                "situation_id": "shop",
                "form_data": FORM_DATA,
                "offer_accepted": True,
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["requires_verification"] is False
    assert "/orders/" in data["redirect_to"]
    mock_mail.assert_not_called()


@pytest.mark.asyncio
async def test_init_order_composes_address_from_subfields(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    form_data = {
        **FORM_DATA,
        "address_city": "Москва",
        "address_street": "Пушкина",
        "address_house": "1",
        "address_apartment": "5",
    }
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 201
    order_id = resp.json()["order_id"]

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    # Подполя собрались в единую строку для шапки документа.
    assert order.form_data["contact_address"] == "г. Москва, ул. Пушкина, д. 1, кв. 5"
    # Сами подполя тоже сохранены — для префилла следующего заказа.
    assert order.form_data["address_city"] == "Москва"


@pytest.mark.asyncio
async def test_init_order_trims_whitespace(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    form_data = {**FORM_DATA, "full_name": "  Иванов Иван  ", "address_city": " Москва "}
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 201
    result = await db_session.execute(select(Order).where(Order.id == resp.json()["order_id"]))
    order = result.scalar_one()
    assert order.form_data["full_name"] == "Иванов Иван"  # краевые пробелы срезаны
    assert order.form_data["address_city"] == "Москва"


@pytest.mark.asyncio
async def test_init_order_rejects_empty_address(
    client: AsyncClient,
    auth_headers: dict,
):
    # Все адресные подполя пустые → документ ушёл бы без адреса заявителя.
    form_data = {k: v for k, v in FORM_DATA.items() if not k.startswith("address_")}
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_init_order_accepts_partial_address(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    # Корпус без дома, без улицы — допустимо (хотя бы одно поле заполнено).
    form_data = {k: v for k, v in FORM_DATA.items() if not k.startswith("address_")}
    form_data |= {"address_city": "Москва", "address_building": "5"}
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 201
    result = await db_session.execute(select(Order).where(Order.id == resp.json()["order_id"]))
    order = result.scalar_one()
    assert order.form_data["contact_address"] == "г. Москва, корп. 5"


@pytest.mark.asyncio
async def test_init_order_rejects_empty_store_address(
    client: AsyncClient,
    auth_headers: dict,
):
    # Ни адреса, ни сайта магазина → непонятно, кому претензия.
    form_data = {k: v for k, v in FORM_DATA.items() if not k.startswith("store_address_")}
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_init_order_accepts_store_site_only(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    # Онлайн-магазин: только сайт, без физического адреса — допустимо.
    form_data = {k: v for k, v in FORM_DATA.items() if not k.startswith("store_address_")}
    form_data |= {"store_site": "www.mvideo.ru"}
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 201
    result = await db_session.execute(select(Order).where(Order.id == resp.json()["order_id"]))
    order = result.scalar_one()
    assert order.form_data["store_address"] == "www.mvideo.ru"


@pytest.mark.asyncio
async def test_init_order_composes_store_address(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": FORM_DATA, "offer_accepted": True},
        )
    assert resp.status_code == 201
    result = await db_session.execute(select(Order).where(Order.id == resp.json()["order_id"]))
    order = result.scalar_one()
    assert order.form_data["store_address"] == "г. Москва, ул. Тверская, д. 1"


@pytest.mark.asyncio
async def test_init_order_rejects_overlong_field(
    client: AsyncClient,
    auth_headers: dict,
):
    form_data = {**FORM_DATA, "address_city": "Я" * 101}  # max_len=100
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": form_data, "offer_accepted": True},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_init_order_rejects_without_offer_acceptance(
    client: AsyncClient,
    auth_headers: dict,
):
    # Без согласия (оферта + ПДн) заказ не создаётся.
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": FORM_DATA, "offer_accepted": False},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_init_order_missing_offer_field_rejected(
    client: AsyncClient,
    auth_headers: dict,
):
    # Поле offer_accepted обязательно — без него схема падает.
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": FORM_DATA},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_init_order_records_offer_acceptance(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    # Факт согласия фиксируется в БД: время, IP, версия (штампует сервер).
    from app.core.consent import CONSENT_VERSION

    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            headers=auth_headers,
            json={"email": "ivan@example.com", "situation_id": "shop", "form_data": FORM_DATA, "offer_accepted": True},
        )
    assert resp.status_code == 201
    result = await db_session.execute(select(Order).where(Order.id == resp.json()["order_id"]))
    order = result.scalar_one()
    assert order.offer_accepted_at is not None
    assert order.offer_version == CONSENT_VERSION
    assert order.offer_accepted_ip  # непустая строка


@pytest.mark.asyncio
async def test_init_order_unknown_situation_rejected(
    client: AsyncClient,
    auth_headers: dict,
):
    resp = await client.post(
        "/api/v1/orders/init",
        headers=auth_headers,
        json={
            "email": "ivan@example.com",
            "situation_id": "nonexistent_situation",
            "form_data": {},
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pay_order_preview_ready_creates_payment(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    # Оплата возможна только когда превью готово (генерация идёт ДО оплаты).
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="preview_ready",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    fake_payment = {
        "payment_id": "yoo-pay-001",
        "confirmation_url": "https://yookassa.ru/pay/001",
    }
    with patch("app.api.v1.orders.create_payment", new_callable=AsyncMock, return_value=fake_payment):
        resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_url"] == fake_payment["confirmation_url"]

    await db_session.refresh(order)
    assert order.status == "pending_payment"
    assert order.payment_url == fake_payment["confirmation_url"]


@pytest.mark.asyncio
async def test_pay_order_pending_can_be_paid_again(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    """Заказ уже в pending_payment (юзер вернулся на страницу) — оплата
    должна работать, row-lock не ломает легитимный повтор."""
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="pending_payment",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    fake_payment = {"payment_id": "yoo-pay-002", "confirmation_url": "https://yookassa.ru/pay/002"}
    with patch("app.api.v1.orders.create_payment", new_callable=AsyncMock, return_value=fake_payment) as mock_pay:
        resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)

    assert resp.status_code == 200
    assert mock_pay.await_count == 1  # ровно один платёж на запрос
    await db_session.refresh(order)
    assert order.yookassa_payment_id == "yoo-pay-002"


@pytest.mark.asyncio
async def test_pay_order_wrong_owner_returns_404(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    other_user = User(email="other@example.com")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    order = Order(
        user_id=other_user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="draft",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pay_order_done_status_rejected(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="done",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_order_returns_order(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="draft",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == order.id
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_orders_returns_user_orders(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    for i in range(3):
        o = Order(user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="draft")
        db_session.add(o)
    await db_session.commit()

    resp = await client.get("/api/v1/orders/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_retry_unpaid_failed_order_regenerates_preview(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    # Не оплачен → retry перегенерирует превью (run_preview_generation), не релиз.
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="failed",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    with patch("app.api.v1.orders.run_preview_generation", new_callable=AsyncMock) as m:
        resp = await client.post(f"/api/v1/orders/{order.id}/retry", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "generating"
    m.assert_called_once()

    await db_session.refresh(order)
    assert order.status == "generating"


@pytest.mark.asyncio
async def test_retry_paid_failed_order_releases(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    # Оплачен (paid_at задан) → retry отпускает документ (run_document_release).
    from datetime import UTC, datetime

    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="failed",
        paid_at=datetime.now(UTC),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    with patch("app.api.v1.orders.run_document_release", new_callable=AsyncMock) as m:
        resp = await client.post(f"/api/v1/orders/{order.id}/retry", headers=auth_headers)

    assert resp.status_code == 200
    m.assert_called_once()


@pytest.mark.asyncio
async def test_retry_non_failed_order_returns_404(
    client: AsyncClient,
    auth_headers: dict,
    user: User,
    db_session: AsyncSession,
):
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        status="done",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/retry", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/orders/")
    assert resp.status_code == 401


async def _make_order(db_session: AsyncSession, user: User, status: str = "done") -> Order:
    order = Order(
        user_id=user.id,
        situation_id="shop",
        form_data=FORM_DATA,
        notification_email="typo@exmaple.com",
        status=status,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.mark.asyncio
async def test_update_order_email_changes_notification_target(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = await _make_order(db_session, user)
    resp = await client.patch(
        f"/api/v1/orders/{order.id}/email",
        headers=auth_headers,
        json={"email": "Fixed@Mail.RU"},
    )
    assert resp.status_code == 200
    assert resp.json()["notification_email"] == "fixed@mail.ru"
    await db_session.refresh(order)
    assert order.notification_email == "fixed@mail.ru"


@pytest.mark.asyncio
async def test_update_order_email_wrong_owner_404(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    other = User(email="other@example.com")
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    order = await _make_order(db_session, other)
    resp = await client.patch(
        f"/api/v1/orders/{order.id}/email", headers=auth_headers, json={"email": "x@y.ru"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resend_done_order_sends_document_ready(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = await _make_order(db_session, user, status="done")
    with patch("app.services.email.send_document_ready", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(f"/api/v1/orders/{order.id}/resend", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
    mock_mail.assert_called_once()
    assert mock_mail.call_args.kwargs["email"] == "typo@exmaple.com"


@pytest.mark.asyncio
async def test_resend_with_email_updates_then_sends_to_new_address(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = await _make_order(db_session, user, status="done")
    with patch("app.services.email.send_document_ready", new_callable=AsyncMock) as mock_mail:
        resp = await client.post(
            f"/api/v1/orders/{order.id}/resend",
            headers=auth_headers,
            json={"email": "correct@mail.ru"},
        )
    assert resp.status_code == 200
    assert resp.json()["email"] == "correct@mail.ru"
    mock_mail.assert_called_once()
    assert mock_mail.call_args.kwargs["email"] == "correct@mail.ru"
    await db_session.refresh(order)
    assert order.notification_email == "correct@mail.ru"


@pytest.mark.asyncio
async def test_resend_draft_order_returns_400(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = await _make_order(db_session, user, status="draft")
    with patch("app.services.email.send_document_ready", new_callable=AsyncMock):
        resp = await client.post(f"/api/v1/orders/{order.id}/resend", headers=auth_headers)
    assert resp.status_code == 400


async def _init_guest_order(client: AsyncClient) -> tuple[str, str]:
    """Создаёт гостевой заказ, возвращает (order_id, order_token)."""
    with patch("app.api.v1.orders.send_magic_link", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/orders/init",
            json={
                "email": "guest@example.com",
                "situation_id": "shop",
                "form_data": FORM_DATA,
                "offer_accepted": True,
            },
        )
    data = resp.json()
    return data["order_id"], data["order_token"]


@pytest.mark.asyncio
async def test_guest_can_pay_with_order_token(client: AsyncClient):
    order_id, token = await _init_guest_order(client)
    fake_payment = {"payment_id": "yoo-g1", "confirmation_url": "https://yookassa.ru/pay/g1"}
    with patch("app.api.v1.orders.create_payment", new_callable=AsyncMock, return_value=fake_payment):
        resp = await client.post(
            f"/api/v1/orders/{order_id}/pay", headers={"X-Order-Token": token}
        )
    assert resp.status_code == 200
    assert resp.json()["payment_url"] == fake_payment["confirmation_url"]


@pytest.mark.asyncio
async def test_guest_pay_wrong_token_returns_404(client: AsyncClient):
    order_id, _ = await _init_guest_order(client)
    resp = await client.post(
        f"/api/v1/orders/{order_id}/pay", headers={"X-Order-Token": "totally-wrong"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_guest_can_view_order_with_token(client: AsyncClient):
    order_id, token = await _init_guest_order(client)
    resp = await client.get(f"/api/v1/orders/{order_id}", headers={"X-Order-Token": token})
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_get_order_without_any_credentials_returns_404(client: AsyncClient):
    order_id, _ = await _init_guest_order(client)
    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_preview_returns_presigned_pages(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    from app.models.document import Document

    order = Order(
        user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="preview_ready"
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    doc = Document(
        order_id=order.id,
        docx_key=f"{order.id}/doc.docx",
        pdf_key=f"{order.id}/doc.pdf",
        preview_keys=[f"{order.id}/preview-0.png", f"{order.id}/preview-1.png"],
    )
    db_session.add(doc)
    await db_session.commit()

    async def _fake_url(key, expires=300):
        return f"https://s3.test/{key}?sig=x"

    with patch("app.services.storage.get_presigned_url", side_effect=_fake_url):
        resp = await client.get(f"/api/v1/orders/{order.id}/preview", headers=auth_headers)

    assert resp.status_code == 200
    pages = resp.json()["pages"]
    assert len(pages) == 2
    assert all(p.startswith("https://s3.test/") for p in pages)


@pytest.mark.asyncio
async def test_preview_empty_when_no_document(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = Order(
        user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="generating"
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.get(f"/api/v1/orders/{order.id}/preview", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["pages"] == []


@pytest.mark.asyncio
async def test_preview_denied_without_access(client: AsyncClient):
    order_id, _ = await _init_guest_order(client)
    resp = await client.get(f"/api/v1/orders/{order_id}/preview")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pay_not_allowed_before_preview_ready(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = Order(
        user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="generating"
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(f"/api/v1/orders/{order.id}/pay", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_public_key_sets_when_empty(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    order = Order(
        user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="preview_ready"
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(
        f"/api/v1/orders/{order.id}/public-key",
        headers=auth_headers,
        json={"public_key": "PUBKEY_NEW"},
    )
    assert resp.status_code == 200
    assert resp.json()["public_key"] == "PUBKEY_NEW"
    await db_session.refresh(user)
    assert user.public_key == "PUBKEY_NEW"


@pytest.mark.asyncio
async def test_register_public_key_does_not_overwrite(
    client: AsyncClient, auth_headers: dict, user: User, db_session: AsyncSession
):
    # Перезапись осиротила бы ранее зашифрованные документы — ключ остаётся прежним.
    user.public_key = "PUBKEY_OLD"
    order = Order(
        user_id=user.id, situation_id="shop", form_data=FORM_DATA, status="preview_ready"
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.post(
        f"/api/v1/orders/{order.id}/public-key",
        headers=auth_headers,
        json={"public_key": "PUBKEY_NEW"},
    )
    assert resp.status_code == 200
    assert resp.json()["public_key"] == "PUBKEY_OLD"
    await db_session.refresh(user)
    assert user.public_key == "PUBKEY_OLD"


@pytest.mark.asyncio
async def test_register_public_key_denied_without_access(client: AsyncClient):
    order_id, _ = await _init_guest_order(client)
    resp = await client.post(
        f"/api/v1/orders/{order_id}/public-key", json={"public_key": "X"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_guest_register_public_key_with_token(client: AsyncClient):
    order_id, token = await _init_guest_order(client)
    resp = await client.post(
        f"/api/v1/orders/{order_id}/public-key",
        headers={"X-Order-Token": token},
        json={"public_key": "GUEST_PUB"},
    )
    assert resp.status_code == 200
    assert resp.json()["public_key"] == "GUEST_PUB"
