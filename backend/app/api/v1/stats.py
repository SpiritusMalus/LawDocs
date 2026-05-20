from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.order import Order

router = APIRouter()


@router.get("/documents-count")
async def get_documents_count(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == "done")
    )
    count = result.scalar_one()
    return {"count": count}
