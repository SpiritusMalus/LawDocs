import hashlib
import hmac
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document
from app.models.order import Order
from app.services.docgen import generate_document
from app.services.email import send_document_ready
from app.services.llm import fill_template

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

    if not _verify_yookassa_signature(body, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event = json.loads(body)
    if event.get("event") != "payment.succeeded":
        return {"received": True}

    payment_id = event["object"]["id"]

    result = await db.execute(select(Order).where(Order.yookassa_payment_id == payment_id))
    order = result.scalar_one_or_none()
    if not order or order.status != "pending_payment":
        return {"received": True}

    order.status = "paid"
    order.paid_at = datetime.now(UTC)
    await db.commit()

    # Генерация документа: LLM заполняет шаблон, docgen собирает файлы
    order.status = "generating"
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
        )

        doc = Document(order_id=order.id, docx_key=docx_key, pdf_key=pdf_key)
        db.add(doc)
        order.status = "done"
        await db.commit()

        # TODO: загрузить email пользователя через joinedload(Order.user) и передать сюда
        await send_document_ready(email="", order_id=order.id)

    except Exception:
        order.status = "failed"
        await db.commit()
        raise

    return {"received": True}
