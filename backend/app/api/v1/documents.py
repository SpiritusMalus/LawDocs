from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.order import Order
from app.models.user import User
from app.services.docgen import get_document_path

router = APIRouter()

_CONTENT_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.get("/{order_id}/download/{fmt}")
async def download_document(
    order_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    if fmt not in _CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format. Use 'docx' or 'pdf'.")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.document))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != "done" or not order.document:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Document not ready yet")

    filename = order.document.docx_key if fmt == "docx" else order.document.pdf_key
    path = get_document_path(order_id, filename)

    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(
        path=path,
        media_type=_CONTENT_TYPES[fmt],
        filename=f"document.{fmt}",
    )
