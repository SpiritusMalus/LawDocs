from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services.docgen import get_presigned_urls

router = APIRouter()


@router.get("/{order_id}", response_model=DocumentOut)
async def get_document(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentOut:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.document))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "done" or not order.document:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Document not ready")

    docx_url, pdf_url = await get_presigned_urls(order.document.docx_key, order.document.pdf_key)

    return DocumentOut(
        id=order.document.id,
        order_id=order_id,
        docx_url=docx_url,
        pdf_url=pdf_url,
        generated_at=order.document.generated_at,
    )
