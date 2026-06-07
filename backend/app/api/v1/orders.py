import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import assert_order_access, get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import get_db
from app.core.consent import CONSENT_VERSION
from app.core.enums import OrderStatus
from app.core.limiter import _get_real_ip, limiter
from app.core.security import (
    generate_guest_token,
    generate_magic_token,
    hash_guest_token,
    hash_magic_token,
)
from app.models.order import Order
from app.models.user import User
from app.schemas.order import (
    OrderEmailUpdate,
    OrderInitOut,
    OrderInitRequest,
    OrderListItem,
    OrderOut,
    OrderPreviewOut,
    OrderPublicKeyIn,
    OrderPublicKeyOut,
    OrderResendRequest,
    PaymentOut,
)
from app.services.address_compose import compose_contact_address, compose_store_address
from app.services.email import send_magic_link
from app.services.generation import run_document_release, run_preview_generation
from app.services.payment import create_payment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[OrderListItem])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderListItem]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.document))
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()
    return [
        OrderListItem(
            id=o.id,
            situation_id=o.situation_id,
            status=o.status,
            amount=o.amount,
            created_at=o.created_at,
            has_document=o.document is not None,
        )
        for o in orders
    ]


@router.post("/init", response_model=OrderInitOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def init_order(
    request: Request,
    body: OrderInitRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
) -> OrderInitOut:
    # Собираем единую строку адреса из структурных подполей (город/улица/дом/…)
    # после валидации схемы. contact_address не входит в wizard-поля, поэтому
    # инжектим его здесь, а не в схеме (иначе check_form_data счёл бы его чужим).
    form_data = dict(body.form_data)
    composed_address = compose_contact_address(form_data)
    if composed_address:
        form_data["contact_address"] = composed_address
    # Аналогично — адрес/сайт магазина-ответчика из store_address_* + store_site.
    composed_store = compose_store_address(form_data)
    if composed_store:
        form_data["store_address"] = composed_store

    # Факт согласия с офертой + обработкой ПДн (галочка на финале визарда).
    # Схема уже отвергла offer_accepted=false; здесь только фиксируем время/IP/версию.
    # Версию проставляет сервер, IP — из доверенного заголовка (см. _get_real_ip).
    consent_fields = dict(
        offer_accepted_at=datetime.now(UTC),
        offer_accepted_ip=_get_real_ip(request),
        offer_version=CONSENT_VERSION,
    )

    # Authenticated flow: skip magic link
    if optional_user:
        order = Order(
            user_id=optional_user.id,
            situation_id=body.situation_id,
            form_data=form_data,
            notification_email=body.email.lower(),
            status=OrderStatus.GENERATING.value,
            **consent_fields,
        )
        db.add(order)
        await db.commit()
        logger.info("order_created_auth", extra={"action": "order_created_auth", "order_id": str(order.id), "situation_id": body.situation_id, "user_id": str(optional_user.id)})
        # Генерация документа + watermarked-превью идёт ДО оплаты (см. эпик).
        background_tasks.add_task(
            run_preview_generation,
            order_id=order.id,
            situation_id=body.situation_id,
            form_data=form_data,
        )
        return OrderInitOut(
            order_id=order.id,
            requires_verification=False,
            redirect_to=f"/orders/{order.id}",
        )

    # Unauthenticated flow: upsert user and send magic link
    email_normalized = body.email.lower()
    result = await db.execute(select(User).where(User.email == email_normalized))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email_normalized)
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(User.email == email_normalized))
            user = result.scalar_one()

    order = Order(
        user_id=user.id,
        situation_id=body.situation_id,
        form_data=form_data,
        notification_email=email_normalized,
        status=OrderStatus.GENERATING.value,
        **consent_fields,
    )
    db.add(order)
    await db.flush()

    # Гостевой токен доступа к ЭТОМУ заказу: гость сразу идёт оплачивать по cookie
    # order_token, без обязательного клика по magic-link. В БД — только хэш.
    guest_token = generate_guest_token()
    order.guest_token_hash = hash_guest_token(guest_token)

    logger.info("order_created", extra={"action": "order_created", "order_id": str(order.id), "situation_id": body.situation_id, "user_id": str(user.id)})

    token = generate_magic_token()
    user.magic_token = hash_magic_token(token)
    user.magic_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
    )
    await db.commit()

    # Magic-link шлём «лучшим усилием» — это теперь опциональный путь (вход с другого
    # устройства / в аккаунт), а НЕ гейт перед оплатой. Сбой почты не должен блокировать
    # гостевую покупку: доступ уже обеспечен order_token.
    magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}&order={order.id}"
    try:
        await send_magic_link(email=str(body.email), url=magic_url)
    except Exception:
        logger.error("order_magic_link_send_failed", extra={"action": "magic_link_send_failed", "order_id": str(order.id)}, exc_info=True)
        if settings.APP_ENV == "development":
            logger.warning("DEV magic link send failed: order=%s token_hash=%s", order.id, hash_magic_token(token))

    # Генерация документа + watermarked-превью идёт ДО оплаты (см. эпик).
    background_tasks.add_task(
        run_preview_generation,
        order_id=order.id,
        situation_id=body.situation_id,
        form_data=form_data,
    )

    return OrderInitOut(
        order_id=order.id,
        requires_verification=False,
        redirect_to=f"/orders/{order.id}",
        order_token=guest_token,
    )


@router.post("/{order_id}/pay", response_model=PaymentOut)
@limiter.limit("10/minute")
async def pay_order(
    request: Request,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
) -> PaymentOut:
    # Лочим строку заказа на время оплаты: двойной клик «Оплатить» не должен
    # создать два платежа в ЮKassa. skip_locked=True — параллельный запрос не
    # ждёт, а сразу получает None и отдаёт 409 (см. ниже). Паттерн как в retry_order.
    # Доступ проверяем по владельцу ИЛИ гостевому токену (assert_order_access),
    # поэтому фильтруем строку только по id, а не по user_id.
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update(skip_locked=True)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        # Либо несуществующий заказ, либо строка уже залочена параллельной оплатой.
        # Различаем: есть ли заказ вообще (без лока).
        exists = await db.execute(select(Order.id).where(Order.id == order_id))
        if exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Платёж уже создаётся. Подождите немного.",
        )
    assert_order_access(order, optional_user, x_order_token)
    # Оплата возможна только когда превью готово (PREVIEW_READY) либо платёж уже
    # создавался (PENDING_PAYMENT — юзер вернулся). До готовности превью платить нечего.
    if order.status not in (OrderStatus.PREVIEW_READY.value, OrderStatus.PENDING_PAYMENT.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order not payable")

    customer_email = order.notification_target
    try:
        payment_data = await create_payment(order_id=order.id, amount=order.amount, customer_email=customer_email)
    except Exception as exc:
        logger.error("payment_create_failed", extra={"action": "payment_create_failed", "order_id": str(order.id)}, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось создать платёж. Попробуйте позже.") from exc

    order.yookassa_payment_id = payment_data["payment_id"]
    order.payment_url = payment_data["confirmation_url"]
    order.status = OrderStatus.PENDING_PAYMENT.value
    await db.commit()

    logger.info("payment_initiated", extra={"action": "payment_initiated", "order_id": str(order.id), "payment_id": payment_data["payment_id"]})

    return PaymentOut(order_id=order.id, payment_url=payment_data["confirmation_url"])


@router.post("/{order_id}/retry")
@limiter.limit("3/minute")
async def retry_order(
    request: Request,
    order_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
) -> dict:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .with_for_update(skip_locked=True)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_order_access(order, optional_user, x_order_token)
    if order.status != OrderStatus.FAILED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not retryable")

    paid = order.paid_at is not None
    order.status = OrderStatus.GENERATING.value
    situation_id = order.situation_id
    form_data = order.form_data
    user_email = order.notification_target
    await db.commit()

    logger.info("order_retry", extra={"action": "order_retry", "order_id": order_id, "paid": paid})

    # Не оплачен → пере-генерируем превью (вернёт PREVIEW_READY). Оплачен → отпускаем
    # документ заново (release сам фолбэкнет на полную генерацию, если документа нет).
    if paid:
        background_tasks.add_task(
            run_document_release,
            order_id=order_id,
            user_email=user_email,
        )
    else:
        background_tasks.add_task(
            run_preview_generation,
            order_id=order_id,
            situation_id=situation_id,
            form_data=form_data,
        )

    return {"status": OrderStatus.GENERATING.value}


async def _resend_status_notification(order_status: str, order_id: str, email: str) -> bool:
    """Шлёт письмо, соответствующее статусу заказа. False — для статуса нечего слать."""
    from app.services.email import (
        send_document_failed,
        send_document_ready,
        send_refund_notification,
    )

    if order_status == OrderStatus.DONE.value:
        await send_document_ready(email=email, order_id=order_id)
    elif order_status == OrderStatus.FAILED.value:
        await send_document_failed(email=email, order_id=order_id)
    elif order_status == OrderStatus.REFUNDED.value:
        await send_refund_notification(email=email, order_id=order_id)
    else:
        return False
    return True


@router.patch("/{order_id}/email", response_model=OrderOut)
@limiter.limit("10/minute")
async def update_order_email(
    request: Request,
    order_id: str,
    body: OrderEmailUpdate,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
) -> Order:
    """Меняет адрес уведомлений заказа. Форму перезаполнять не нужно — правим одно поле.

    Не трогает identity-почту аккаунта (User.email): это только адрес доставки писем.
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_order_access(order, optional_user, x_order_token)

    order.notification_email = body.email.lower()
    await db.commit()
    await db.refresh(order)
    logger.info("order_email_updated", extra={"action": "order_email_updated", "order_id": order_id})
    return order


@router.post("/{order_id}/resend")
@limiter.limit("5/minute")
async def resend_order_notification(
    request: Request,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
    body: OrderResendRequest | None = None,
) -> dict:
    """Повторно шлёт письмо по заказу; опционально сперва правит адрес уведомлений.

    Закрывает кейс «опечатался в почте → не пришёл документ»: пользователь меняет
    адрес и пересылает письмо, не оформляя заказ заново.
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_order_access(order, optional_user, x_order_token)

    # Захватываем значения ДО commit: после него атрибуты ORM-объекта истекают,
    # а ленивая подгрузка в async-сессии бросит исключение (тот же паттерн, что в webhook).
    if body and body.email:
        order.notification_email = body.email.lower()
    order_status = order.status
    email = order.notification_target
    if body and body.email:
        await db.commit()

    try:
        sent = await _resend_status_notification(order_status, order_id, email)
    except Exception as exc:
        logger.error("order_resend_failed", extra={"action": "order_resend_failed", "order_id": order_id}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось отправить письмо. Попробуйте позже.",
        ) from exc

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для текущего статуса заказа пересылать нечего.",
        )

    logger.info("order_notification_resent", extra={"action": "order_notification_resent", "order_id": order_id})
    return {"status": "sent", "email": email}


@router.get("/{order_id}/preview", response_model=OrderPreviewOut)
@limiter.limit("30/minute")
async def get_order_preview(
    request: Request,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
) -> OrderPreviewOut:
    """Watermarked-превью (по странице) — доступно ДО оплаты. Чистый файл — нет."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.user), selectinload(Order.document))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_order_access(order, optional_user, x_order_token)

    document = order.document
    if not document or not document.preview_keys:
        return OrderPreviewOut(pages=[])

    from app.services.storage import get_presigned_url

    pages = [await get_presigned_url(key, expires=900) for key in document.preview_keys]
    return OrderPreviewOut(pages=pages)


@router.post("/{order_id}/public-key", response_model=OrderPublicKeyOut)
@limiter.limit("10/minute")
async def register_order_public_key(
    request: Request,
    order_id: str,
    body: OrderPublicKeyIn,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
) -> OrderPublicKeyOut:
    """Регистрирует публичный E2EE-ключ для пользователя этого заказа (гость — по
    order_token). Ставит user.public_key ТОЛЬКО если он пуст: перезапись осиротила бы
    ранее зашифрованные документы. Возвращает эффективный (уже стоявший либо новый) ключ.
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_order_access(order, optional_user, x_order_token)

    user = order.user
    # Захватываем эффективный ключ ДО commit (после него атрибуты истекают).
    effective = user.public_key or body.public_key
    if not user.public_key:
        user.public_key = body.public_key
        await db.commit()
        logger.info("order_public_key_set", extra={"action": "order_public_key_set", "order_id": order_id})

    return OrderPublicKeyOut(public_key=effective)


@router.get("/{order_id}", response_model=OrderOut)
@limiter.limit("30/minute")
async def get_order(
    request: Request,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
    x_order_token: str | None = Header(default=None),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    assert_order_access(order, optional_user, x_order_token)
    return order
