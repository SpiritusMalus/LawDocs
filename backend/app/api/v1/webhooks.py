import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.order import Order
from app.services.docgen import generate_document, generate_instruction, get_document_path
from app.services.email import send_document_failed, send_document_ready
from app.services.llm import fill_instruction, fill_template

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_yookassa_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.YOOKASSA_SECRET_KEY.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/yookassa", status_code=status.HTTP_200_OK)
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    body = await request.body()
    signature = request.headers.get("X-Content-SHA256", "")

    if settings.YOOKASSA_SECRET_KEY and not _verify_yookassa_signature(body, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event = json.loads(body)
    if event.get("event") != "payment.succeeded":
        return {"received": True}

    payment_id = event["object"]["id"]

    result = await db.execute(
        select(Order)
        .where(Order.yookassa_payment_id == payment_id)
        .options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order or order.status != "pending_payment":
        return {"received": True}

    # Atomically transition paid → generating in one commit
    order.status = "generating"
    order.paid_at = datetime.now(UTC)
    await db.commit()

    try:
        filled_content = await fill_template(
            situation_id=order.situation_id,
            form_data=order.form_data,
        )
        docx_key, pdf_key = await generate_document(
            order_id=order.id,
            situation_id=order.situation_id,
            content=filled_content,
            form_data=order.form_data,
        )

        instruction_pdf_key = None
        try:
            from app.situations.registry import registry as _registry
            _config = _registry.get(order.situation_id)
            _legal_refs = [ref.model_dump() for ref in (_config.legal_refs if _config else [])]
            instruction_content = await fill_instruction(
                situation_id=order.situation_id,
                form_data=order.form_data,
            )
            instruction_pdf_key = await generate_instruction(
                order_id=order.id,
                situation_id=order.situation_id,
                content=instruction_content,
                legal_refs=_legal_refs,
            )
        except Exception:
            logger.exception("Instruction generation failed for order %s, continuing without it", order.id)

        doc = Document(
            order_id=order.id,
            docx_key=docx_key,
            pdf_key=pdf_key,
            instruction_pdf_key=instruction_pdf_key,
        )
        db.add(doc)
        order.status = "done"
        await db.commit()

        pdf_path = get_document_path(order.id, pdf_key)
        instruction_path = get_document_path(order.id, instruction_pdf_key) if instruction_pdf_key else None
        await send_document_ready(
            email=order.user.email,
            order_id=order.id,
            pdf_path=pdf_path,
            instruction_path=instruction_path,
        )

    except Exception:
        logger.exception("Document generation failed for order %s", order.id)
        order.status = "failed"
        await db.commit()
        try:
            await send_document_failed(email=order.user.email, order_id=order.id)
        except Exception:
            logger.exception("Failed to send failure notification for order %s", order.id)
        # Return 200 so ЮKassa doesn't retry — failure is handled in app
        return {"received": True, "error": "generation_failed"}

    return {"received": True}
