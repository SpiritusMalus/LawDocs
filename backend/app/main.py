import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import delete, not_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.limiter import limiter
from app.api.v1 import auth, documents, orders, situations, webhooks
from app.models.order import Order
from app.models.user import User
from app.situations.registry import registry


class JsonFormatter(logging.Formatter):
  def format(self, record: logging.LogRecord) -> str:
    log_obj = {
        "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
        "level": record.levelname,
        "logger": record.name,
        "msg": record.getMessage(),
    }
    for key in ("action", "user_id", "order_id", "situation_id", "email_domain", "ip", "payment_id", "reason"):
      if hasattr(record, key):
        log_obj[key] = getattr(record, key)
    if record.exc_info:
      log_obj["exception"] = self.formatException(record.exc_info)
    return json.dumps(log_obj, ensure_ascii=False, default=str)


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)


_cleanup_logger = logging.getLogger("cleanup")


async def _cleanup_draft_orders() -> None:
    """Каждый час удаляет draft-заказы старше 24 часов и осиротевших пользователей.

    Черновик создаётся до того, как пользователь кликает magic link. Если он
    не завершил авторизацию — ПДн из form_data остаются в БД навсегда.
    Удаляем их через 24 часа, чтобы не копить чувствительные данные.
    """
    while True:
        await asyncio.sleep(60 * 60)  # первый запуск через час после старта
        try:
            cutoff = datetime.now(UTC) - timedelta(hours=24)
            async with AsyncSessionLocal() as db:
                # 1. Удаляем старые черновики
                result = await db.execute(
                    delete(Order)
                    .where(Order.status == "draft", Order.created_at < cutoff)
                    .returning(Order.id)
                )
                deleted_orders = result.rowcount

                # 2. Удаляем пользователей без заказов с истёкшим magic-токеном
                #    (так и не прошедших авторизацию)
                subq = select(Order.user_id).distinct()
                result = await db.execute(
                    delete(User)
                    .where(
                        not_(User.id.in_(subq)),
                        User.magic_token_expires_at < datetime.now(UTC),
                    )
                    .returning(User.id)
                )
                deleted_users = result.rowcount

                await db.commit()

            if deleted_orders or deleted_users:
                _cleanup_logger.info(
                    "draft_cleanup_done",
                    extra={
                        "action": "draft_cleanup_done",
                        "deleted_orders": deleted_orders,
                        "deleted_users": deleted_users,
                    },
                )
        except Exception:
            _cleanup_logger.exception("draft_cleanup_failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configs_dir = Path(__file__).parent / "situations" / "configs"
    registry.load(configs_dir)
    task = asyncio.create_task(_cleanup_draft_orders())
    yield
    task.cancel()


app = FastAPI(
    title="LawDocs API",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(situations.router, prefix="/api/v1/situations", tags=["situations"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "situations_loaded": len(registry)}
