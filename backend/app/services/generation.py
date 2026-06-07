"""
Генерация документов: основная фоновая задача.

Выделена отдельно, чтобы её могли вызывать orders.py (retry по кнопке)
и main.py (_auto_retry_loop — автоматический retry по cron).
"""

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.enums import OrderStatus
from app.models.order import Order
from app.models.user import User

logger = logging.getLogger(__name__)


def _resolve_legal_refs(config, form_data: dict) -> list[dict]:
    refs = list(config.legal_refs)
    for key, branch_refs in config.legal_refs_by_branch.items():
        field_id, _, value = key.partition(":")
        if form_data.get(field_id) == value:
            refs.extend(branch_refs)
    seen: set[str] = set()
    result = []
    for r in refs:
        if r.law not in seen:
            seen.add(r.law)
            result.append(r)
    return [r.model_dump() for r in result]


def _apply_calculator(situation_id: str, form_data: dict) -> dict:
    """Прогоняет form_data через калькулятор ситуации, если он есть."""
    from app.services.calculators import SITUATION_CALCULATORS

    if situation_id in SITUATION_CALCULATORS:
        return SITUATION_CALCULATORS[situation_id](form_data)
    return form_data


async def _generate_main_document(order_id: str, situation_id: str, form_data: dict) -> tuple[str, str]:
    """Рендерит основной документ из (уже обсчитанных) данных формы."""
    from app.services.docgen import generate_document
    from app.services.llm import fill_template

    body, header, title = await fill_template(situation_id=situation_id, form_data=form_data)
    return await generate_document(
        order_id=order_id,
        situation_id=situation_id,
        body=body,
        header=header,
        title=title,
        form_data=form_data,
    )


async def _generate_instruction(order_id: str, situation_id: str, form_data: dict) -> str | None:
    """Рендерит PDF-инструкцию. Опциональна: сбой не валит заказ."""
    from app.services.docgen import generate_instruction
    from app.services.llm import fill_instruction

    try:
        from app.situations.registry import registry

        config = registry.get(situation_id)
        legal_refs = _resolve_legal_refs(config, form_data) if config else []
        content = await fill_instruction(situation_id=situation_id, form_data=form_data)
        return await generate_instruction(
            order_id=order_id,
            situation_id=situation_id,
            content=content,
            legal_refs=legal_refs,
        )
    except Exception:
        logger.exception("Instruction generation failed for order %s", order_id)
        return None


async def _maybe_encrypt_files(order_id: str, user_obj: User | None, file_keys: list[str]) -> bool:
    """Шифрует файлы публичным ключом юзера, если он задан.

    Инструкция не шифруется — она не содержит ПДн. При сбое шифрования
    оставляем plaintext (заказ не должен падать из-за E2EE).
    """
    if not (user_obj and user_obj.public_key):
        return False
    from app.services.e2ee_file import encrypt_file_for_user
    from app.services.storage import download_bytes, upload_bytes

    try:
        pub = user_obj.public_key
        for key in (k for k in file_keys if k):
            raw = await download_bytes(key)
            await upload_bytes(key, encrypt_file_for_user(raw, pub))
        logger.info("Files encrypted for order %s", order_id)
        return True
    except Exception:
        logger.exception("File encryption failed for order %s — uploading plaintext", order_id)
        return False


async def _finalize_success(
    db,
    order: Order,
    user_obj: User | None,
    user_email: str,
    order_id: str,
    docx_key: str,
    pdf_key: str,
    instruction_pdf_key: str | None,
    user_encrypted: bool,
) -> None:
    """Сохраняет документ, помечает заказ done, шлёт письмо и стирает ПДн."""
    from app.models.document import Document
    from app.services.email import send_document_ready

    # Идемпотентно: документ мог уже существовать (превью-генерация / повторный
    # вызов) — обновляем, а не вставляем второй (order_id уникален).
    existing = await db.execute(select(Document).where(Document.order_id == order_id))
    doc = existing.scalar_one_or_none()
    if doc is None:
        doc = Document(order_id=order_id)
        db.add(doc)
    doc.docx_key = docx_key
    doc.pdf_key = pdf_key
    doc.instruction_pdf_key = instruction_pdf_key
    doc.user_encrypted = user_encrypted
    order.status = OrderStatus.DONE.value
    order.payment_url = None
    if user_obj:
        user_obj.completed_orders_count += 1
    await db.commit()

    try:
        await send_document_ready(email=user_email, order_id=order_id)
    except Exception:
        logger.exception("Email delivery failed for order %s — document is ready, form_data preserved for retry", order_id)

    # Privacy: стираем ПДн только после успешной доставки письма.
    # Если email упал — form_data сохраняется для повторной отправки.
    # Отдельный commit: сбой стирания не должен откатить status=done.
    try:
        order.form_data = {}
        await db.commit()
    except Exception:
        logger.exception("Failed to wipe form_data for order %s", order_id)


async def _send_failure_notifications(
    order: Order, order_id: str, situation_id: str, user_email: str, refunded: bool
) -> None:
    """Шлёт юзеру письмо и Telegram-алерт о провале/возврате."""
    from app.services.email import send_document_failed, send_refund_notification

    is_refunded = order.status == OrderStatus.REFUNDED.value
    try:
        if is_refunded:
            await send_refund_notification(email=user_email, order_id=order_id)
        else:
            await send_document_failed(email=user_email, order_id=order_id)
    except Exception:
        logger.exception("Failed to send failure notification for order %s", order_id)

    try:
        from app.services.notifications import format_order_alert, send_telegram_alert

        if is_refunded:
            alert = format_order_alert(
                "refund",
                order_id=order_id,
                situation_id=situation_id,
                user_email=user_email,
                payment_id=order.yookassa_payment_id,
                refunded=refunded,
            )
        else:
            alert = format_order_alert(
                "failed",
                order_id=order_id,
                situation_id=situation_id,
                user_email=user_email,
            )
        await send_telegram_alert(alert)
    except Exception:
        logger.exception("Failed to send Telegram alert for order %s", order_id)


async def _handle_generation_failure(
    db, order: Order, order_id: str, situation_id: str, user_email: str, notify_on_failure: bool
) -> None:
    """Все retry исчерпаны: возвращаем деньги (если можем) и уведомляем."""
    logger.exception("Document generation failed for order %s", order_id)
    refunded = False
    if notify_on_failure and order.yookassa_payment_id:
        from app.services.payment import refund_payment

        try:
            refunded = await refund_payment(order.yookassa_payment_id, order.amount)
        except Exception:
            logger.exception("Refund request failed for order %s", order_id)
            refunded = False
        order.status = OrderStatus.REFUNDED.value
        order.form_data = {}
    else:
        order.status = OrderStatus.FAILED.value
    await db.commit()

    if notify_on_failure:
        await _send_failure_notifications(order, order_id, situation_id, user_email, refunded)


async def run_document_generation(
    order_id: str,
    situation_id: str,
    form_data: dict,
    user_email: str,
    notify_on_failure: bool = True,
) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return

        try:
            form_data = _apply_calculator(situation_id, form_data)
            docx_key, pdf_key = await _generate_main_document(order_id, situation_id, form_data)
            instruction_pdf_key = await _generate_instruction(order_id, situation_id, form_data)

            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user_obj = user_result.scalar_one_or_none()
            user_encrypted = await _maybe_encrypt_files(order_id, user_obj, [docx_key, pdf_key])

            await _finalize_success(
                db, order, user_obj, user_email, order_id,
                docx_key, pdf_key, instruction_pdf_key, user_encrypted,
            )
        except Exception:
            await _handle_generation_failure(
                db, order, order_id, situation_id, user_email, notify_on_failure
            )


async def _build_and_store_preview(order_id: str, pdf_key: str) -> list[str]:
    """Растеризует чистый PDF в watermarked-PNG (по странице) и кладёт в storage."""
    import asyncio

    from app.services.docgen import s3_key
    from app.services.preview import render_watermarked_pngs
    from app.services.storage import download_bytes, upload_bytes

    pdf_bytes = await download_bytes(pdf_key)
    loop = asyncio.get_running_loop()
    pages = await loop.run_in_executor(None, render_watermarked_pngs, pdf_bytes)

    keys: list[str] = []
    for i, png in enumerate(pages):
        key = s3_key(order_id, f"preview-{i}.png")
        await upload_bytes(key, png)
        keys.append(key)
    return keys


async def run_preview_generation(order_id: str, situation_id: str, form_data: dict) -> None:
    """ДО оплаты: генерирует чистый документ + watermarked-превью, ставит PREVIEW_READY.

    Денег ещё нет — при сбое просто FAILED (без рефанда). Чистый docx/pdf лежат в
    storage под gate'ом оплаты; наружу до оплаты уходит только превью.
    """
    from app.models.document import Document

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return

        try:
            form_data = _apply_calculator(situation_id, form_data)
            docx_key, pdf_key = await _generate_main_document(order_id, situation_id, form_data)
            instruction_pdf_key = await _generate_instruction(order_id, situation_id, form_data)
            preview_keys = await _build_and_store_preview(order_id, pdf_key)

            doc = Document(
                order_id=order_id,
                docx_key=docx_key,
                pdf_key=pdf_key,
                instruction_pdf_key=instruction_pdf_key,
                user_encrypted=False,
                preview_keys=preview_keys,
            )
            db.add(doc)
            order.status = OrderStatus.PREVIEW_READY.value
            await db.commit()
            logger.info("preview_ready for order %s (%d pages)", order_id, len(preview_keys))
        except Exception:
            logger.exception("Preview generation failed for order %s", order_id)
            order.status = OrderStatus.FAILED.value
            await db.commit()


async def _finalize_release(
    db, order: Order, document, user_obj: User | None, user_email: str, order_id: str, user_encrypted: bool
) -> None:
    """Отпускает уже сгенерированный документ: DONE + письмо + стирание ПДн."""
    from app.services.email import send_document_ready

    document.user_encrypted = user_encrypted
    order.status = OrderStatus.DONE.value
    order.payment_url = None
    if user_obj:
        user_obj.completed_orders_count += 1
    await db.commit()

    try:
        await send_document_ready(email=user_email, order_id=order_id)
    except Exception:
        logger.exception("Email delivery failed for order %s (release) — document ready", order_id)

    try:
        order.form_data = {}
        await db.commit()
    except Exception:
        logger.exception("Failed to wipe form_data for order %s", order_id)


async def run_document_release(order_id: str, user_email: str, notify_on_failure: bool = True) -> None:
    """ПОСЛЕ оплаты: отпускает уже готовый документ (DONE + письмо + шифрование под
    ключ юзера). Документ обычно уже есть (оплата возможна только из PREVIEW_READY);
    холодный фолбэк — если его нет, генерируем полностью старым путём.
    """
    from app.models.document import Document

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return

        situation_id = order.situation_id
        form_data = order.form_data

        doc_result = await db.execute(select(Document).where(Document.order_id == order_id))
        document = doc_result.scalar_one_or_none()

    if document is None:
        # Холодный фолбэк: превью не сгенерилось, но оплата прошла — генерируем полностью.
        logger.warning("release: no document for paid order %s — full generation fallback", order_id)
        await run_document_generation(
            order_id=order_id, situation_id=situation_id, form_data=form_data,
            user_email=user_email, notify_on_failure=notify_on_failure,
        )
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return
        doc_result = await db.execute(select(Document).where(Document.order_id == order_id))
        document = doc_result.scalar_one_or_none()
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user_obj = user_result.scalar_one_or_none()

        try:
            user_encrypted = await _maybe_encrypt_files(
                order_id, user_obj, [document.docx_key, document.pdf_key]
            )
            await _finalize_release(db, order, document, user_obj, user_email, order_id, user_encrypted)
        except Exception:
            logger.exception("Document release failed for order %s — order stays paid for retry", order_id)
