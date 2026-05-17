import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.limiter import limiter
from app.core.security import generate_magic_token, hash_magic_token
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderInitOut, OrderInitRequest, OrderListItem, OrderOut, PaymentOut
from app.services.email import send_magic_link
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
    db: AsyncSession = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
) -> OrderInitOut:
    # Authenticated flow: skip magic link
    if optional_user:
        order = Order(
            user_id=optional_user.id,
            situation_id=body.situation_id,
            form_data=body.form_data,
            status="draft",
        )
        db.add(order)
        await db.commit()
        logger.info("order_created_auth", extra={"action": "order_created_auth", "order_id": str(order.id), "situation_id": body.situation_id, "user_id": str(optional_user.id)})
        return OrderInitOut(
            order_id=order.id,
            requires_verification=False,
            redirect_to=f"/orders/{order.id}",
        )

    # Unauthenticated flow: upsert user and send magic link
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=str(body.email))
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(User.email == body.email))
            user = result.scalar_one()

    order = Order(
        user_id=user.id,
        situation_id=body.situation_id,
        form_data=body.form_data,
        status="draft",
    )
    db.add(order)
    await db.flush()

    logger.info("order_created", extra={"action": "order_created", "order_id": str(order.id), "situation_id": body.situation_id, "user_id": str(user.id)})

    token = generate_magic_token()
    user.magic_token = hash_magic_token(token)
    user.magic_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.MAGIC_LINK_EXPIRE_MINUTES
    )
    await db.commit()

    magic_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}&order={order.id}"
    try:
        await send_magic_link(email=str(body.email), url=magic_url)
    except Exception as exc:
        logger.error("order_magic_link_send_failed", extra={"action": "magic_link_send_failed", "order_id": str(order.id)}, exc_info=True)
        if settings.APP_ENV == "development":
            logger.warning("DEV magic link send failed: order=%s token_hash=%s", order.id, hash_magic_token(token))
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не удалось отправить письмо. Попробуйте ещё раз.",
            ) from exc

    return OrderInitOut(order_id=order.id)


@router.post("/{order_id}/pay", response_model=PaymentOut)
async def pay_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentOut:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status not in ("draft", "pending_payment"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order not payable")

    try:
        payment_data = await create_payment(order_id=order.id, amount=order.amount, customer_email=current_user.email)
    except Exception as exc:
        logger.error("payment_create_failed", extra={"action": "payment_create_failed", "order_id": str(order.id), "user_id": str(current_user.id)}, exc_info=True)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось создать платёж. Попробуйте позже.") from exc

    order.yookassa_payment_id = payment_data["payment_id"]
    order.payment_url = payment_data["confirmation_url"]
    order.status = "pending_payment"
    await db.commit()

    logger.info("payment_initiated", extra={"action": "payment_initiated", "order_id": str(order.id), "payment_id": payment_data["payment_id"], "user_id": str(current_user.id)})

    return PaymentOut(order_id=order.id, payment_url=payment_data["confirmation_url"])


async def _run_document_generation(order_id: str, situation_id: str, form_data: dict, user_email: str) -> None:
    from app.models.document import Document
    from app.services.docgen import generate_document, generate_instruction
    from app.services.email import send_document_failed, send_document_ready
    from app.services.llm import fill_instruction, fill_template
    from app.services.storage import download_bytes

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return
        try:
            filled_content = await fill_template(situation_id=situation_id, form_data=form_data)
            docx_key, pdf_key = await generate_document(
                order_id=order_id,
                situation_id=situation_id,
                content=filled_content,
                form_data=form_data,
            )
            instruction_pdf_key = None
            try:
                from app.situations.registry import registry as _registry
                _config = _registry.get(situation_id)
                _legal_refs = [ref.model_dump() for ref in (_config.legal_refs if _config else [])]
                instruction_content = await fill_instruction(situation_id=situation_id, form_data=form_data)
                instruction_pdf_key = await generate_instruction(
                    order_id=order_id,
                    situation_id=situation_id,
                    content=instruction_content,
                    legal_refs=_legal_refs,
                )
            except Exception:
                logger.exception("Instruction generation failed for retry order %s", order_id)

            doc = Document(
                order_id=order_id,
                docx_key=docx_key,
                pdf_key=pdf_key,
                instruction_pdf_key=instruction_pdf_key,
            )
            db.add(doc)
            order.status = "done"
            order.payment_url = None
            await db.commit()

            pdf_bytes = await download_bytes(pdf_key)
            instruction_bytes = await download_bytes(instruction_pdf_key) if instruction_pdf_key else None
            await send_document_ready(
                email=user_email,
                order_id=order_id,
                pdf_bytes=pdf_bytes,
                pdf_filename=pdf_key.split("/")[-1],
                instruction_bytes=instruction_bytes,
                instruction_filename=instruction_pdf_key.split("/")[-1] if instruction_pdf_key else "instrukciya.pdf",
            )
        except Exception:
            logger.exception("Retry generation failed for order %s", order_id)
            order.status = "failed"
            await db.commit()
            try:
                await send_document_failed(email=user_email, order_id=order_id)
            except Exception:
                logger.exception("Failed to send failure notification for retry order %s", order_id)


@router.post("/{order_id}/retry")
async def retry_order(
    order_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id, Order.status == "failed")
        .with_for_update(skip_locked=True)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or not retryable")

    order.status = "generating"
    await db.commit()

    logger.info("order_retry", extra={"action": "order_retry", "order_id": order_id, "user_id": str(current_user.id)})

    background_tasks.add_task(
        _run_document_generation,
        order_id=order.id,
        situation_id=order.situation_id,
        form_data=order.form_data,
        user_email=str(order.user.email),
    )

    return {"status": "generating"}


@router.get("/{order_id}", response_model=OrderOut)
@limiter.limit("30/minute")
async def get_order(
    request: Request,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Order:
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
