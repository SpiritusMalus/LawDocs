"""
Генерация документов: основная фоновая задача.

Выделена отдельно, чтобы её могли вызывать orders.py (retry по кнопке)
и main.py (_auto_retry_loop — автоматический retry по cron).
"""

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.order import Order
from app.models.user import User

logger = logging.getLogger(__name__)


async def run_document_generation(
    order_id: str,
    situation_id: str,
    form_data: dict,
    user_email: str,
    notify_on_failure: bool = True,
) -> None:
    from app.models.document import Document
    from app.services.docgen import generate_document, generate_instruction
    from app.services.email import send_document_failed, send_document_ready
    from app.services.llm import fill_instruction, fill_template

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return
        try:
            from app.services.calculators import SITUATION_CALCULATORS
            if situation_id in SITUATION_CALCULATORS:
                form_data = SITUATION_CALCULATORS[situation_id](form_data)
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
                logger.exception("Instruction generation failed for order %s", order_id)

            # Шифруем файлы публичным ключом юзера, если он задан.
            # Инструкция не шифруется — она не содержит ПДн.
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user_obj = user_result.scalar_one_or_none()
            user_encrypted = False
            if user_obj and user_obj.public_key:
                from app.services.e2ee_file import encrypt_file_for_user
                from app.services.storage import download_bytes, upload_bytes
                try:
                    pub = user_obj.public_key
                    for key in (k for k in [docx_key, pdf_key] if k):
                        raw = await download_bytes(key)
                        await upload_bytes(key, encrypt_file_for_user(raw, pub))
                    user_encrypted = True
                    logger.info("Files encrypted for order %s", order_id)
                except Exception:
                    logger.exception("File encryption failed for order %s — uploading plaintext", order_id)

            doc = Document(
                order_id=order_id,
                docx_key=docx_key,
                pdf_key=pdf_key,
                instruction_pdf_key=instruction_pdf_key,
                user_encrypted=user_encrypted,
            )
            db.add(doc)
            order.status = "done"
            order.payment_url = None

            if user_obj:
                user_obj.completed_orders_count += 1

            await db.commit()

            await send_document_ready(email=user_email, order_id=order_id)

            # Privacy: документ доставлен — персональные данные больше не нужны.
            # Стираем отдельным commit только после успеха; на failed form_data
            # сохраняется для retry (поэтому стирание не в транзакции status=done:
            # сбой письма не должен оставить заказ без данных для повторной генерации).
            order.form_data = {}
            await db.commit()
        except Exception:
            logger.exception("Document generation failed for order %s", order_id)
            order.status = "failed"
            await db.commit()
            if notify_on_failure:
                try:
                    await send_document_failed(email=user_email, order_id=order_id)
                except Exception:
                    logger.exception("Failed to send failure notification for order %s", order_id)
                try:
                    from app.services.notifications import send_telegram_alert
                    await send_telegram_alert(
                        f"❌ <b>Order failed</b>\n"
                        f"order_id: <code>{order_id}</code>\n"
                        f"situation: {situation_id}\n"
                        f"email: {user_email}"
                    )
                except Exception:
                    logger.exception("Failed to send Telegram alert for order %s", order_id)
