import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.enums import OrderStatus
from app.models.order import Order
from app.models.user import User
from app.schemas.document import DocumentDownloadInfo
from app.services.storage import get_presigned_url

router = APIRouter()

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


async def _get_order_with_document(
    order_id: str,
    current_user: User,
    db: AsyncSession,
):
    if not _UUID_RE.match(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order_id format")
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(selectinload(Order.document))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.DONE.value or not order.document:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Document not ready yet")
    return order


@router.get("/{order_id}/download/instruction")
async def download_instruction(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    order = await _get_order_with_document(order_id, current_user, db)

    if not order.document.instruction_pdf_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instruction not available for this order")

    url = await get_presigned_url(order.document.instruction_pdf_key)
    return RedirectResponse(url=url, status_code=302)


@router.get("/{order_id}/download/{fmt}")
async def download_document(
    order_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format. Use 'docx' or 'pdf'.")

    order = await _get_order_with_document(order_id, current_user, db)
    key = order.document.docx_key if fmt == "docx" else order.document.pdf_key

    url = await get_presigned_url(key)
    return RedirectResponse(url=url, status_code=302)


@router.get("/{order_id}/download-info/{fmt}", response_model=DocumentDownloadInfo)
async def download_info(
    order_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDownloadInfo:
    """Возвращает presigned URL и флаг шифрования. Для зашифрованных файлов
    фронт скачивает байты сам и расшифровывает приватным ключом юзера."""
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format. Use 'docx' or 'pdf'.")

    order = await _get_order_with_document(order_id, current_user, db)
    key = order.document.docx_key if fmt == "docx" else order.document.pdf_key
    url = await get_presigned_url(key, expires=900)

    filename = f"lawdocs_{order_id[:8]}.{fmt}"
    return DocumentDownloadInfo(
        url=url,
        is_encrypted=order.document.user_encrypted,
        filename=filename,
    )
