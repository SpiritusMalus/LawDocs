import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.limiter import limiter
from app.api.v1 import auth, documents, orders, reviews, situations, stats, users, webhooks
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
_law_monitor_logger = logging.getLogger("law_monitor")
_auto_retry_logger = logging.getLogger("auto_retry")

_MAX_AUTO_RETRIES = 5
_AUTO_RETRY_INTERVAL = 15 * 60  # 15 минут


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

                # 3. Обнуляем form_data в done/failed-заказах старше 30 дней (152-ФЗ).
                #    failed-заказы не имеют paid_at — используем created_at как fallback.
                pii_cutoff = datetime.now(UTC) - timedelta(days=30)
                result = await db.execute(
                    update(Order)
                    .where(
                        Order.status.in_(["done", "failed"]),
                        func.coalesce(Order.paid_at, Order.created_at) < pii_cutoff,
                    )
                    .values(form_data={})
                    .returning(Order.id)
                )
                purged_orders = result.rowcount

                await db.commit()

            if deleted_orders or deleted_users or purged_orders:
                _cleanup_logger.info(
                    "draft_cleanup_done",
                    extra={
                        "action": "draft_cleanup_done",
                        "deleted_orders": deleted_orders,
                        "deleted_users": deleted_users,
                        "purged_pii_orders": purged_orders,
                    },
                )
        except Exception:
            _cleanup_logger.exception("draft_cleanup_failed")


async def _auto_retry_loop() -> None:
    """Каждые 15 минут ищет failed-заказы с оплатой и повторяет генерацию (до 5 попыток)."""
    while True:
        await asyncio.sleep(_AUTO_RETRY_INTERVAL)
        try:
            from app.services.generation import run_document_generation
            async with AsyncSessionLocal() as db:
                # Watchdog: заказы stuck в "generating" >30 мин → failed
                # (сервер упал во время генерации; используем paid_at как proxy,
                # т.к. generating всегда наступает после оплаты)
                watchdog_cutoff = datetime.now(UTC) - timedelta(minutes=30)
                await db.execute(
                    update(Order)
                    .where(
                        Order.status == "generating",
                        Order.paid_at < watchdog_cutoff,
                    )
                    .values(status="failed")
                )

                result = await db.execute(
                    select(Order)
                    .where(
                        Order.status == "failed",
                        Order.paid_at.is_not(None),
                        Order.auto_retry_count < _MAX_AUTO_RETRIES,
                    )
                    .options(selectinload(Order.user))
                    .with_for_update(skip_locked=True)
                )
                orders_to_retry = result.scalars().all()
                for order in orders_to_retry:
                    order.auto_retry_count += 1
                    order.status = "generating"
                retry_tasks = [
                    (
                        str(o.id),
                        o.situation_id,
                        o.form_data,
                        str(o.user.email),
                        o.auto_retry_count >= _MAX_AUTO_RETRIES,
                    )
                    for o in orders_to_retry
                ]
                await db.commit()

            for order_id, situation_id, form_data, user_email, is_last in retry_tasks:
                _auto_retry_logger.info(
                    "auto_retry_triggered",
                    extra={"action": "auto_retry_triggered", "order_id": order_id},
                )
                asyncio.create_task(
                    run_document_generation(
                        order_id=order_id,
                        situation_id=situation_id,
                        form_data=form_data,
                        user_email=user_email,
                        notify_on_failure=is_last,
                    )
                )
        except Exception:
            _auto_retry_logger.exception("auto_retry_loop_failed")


async def _law_monitor_loop() -> None:
    """Запускает мониторинг законодательства 1-го числа каждого месяца в 09:00 UTC."""
    while True:
        now = datetime.now(UTC)
        if now.month == 12:
            next_run = datetime(now.year + 1, 1, 1, 9, 0, tzinfo=UTC)
        else:
            next_run = datetime(now.year, now.month + 1, 1, 9, 0, tzinfo=UTC)
        delay = (next_run - now).total_seconds()
        await asyncio.sleep(delay)
        try:
            from app.services.law_monitor import run_law_monitor
            await run_law_monitor()
        except Exception:
            _law_monitor_logger.exception("law_monitor_failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.APP_ENV == "production" and not settings.fernet_keys_list:
        raise RuntimeError(
            "FERNET_KEY (или FERNET_KEYS) не задан в production. "
            "Сгенерируйте: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    configs_dir = Path(__file__).parent / "situations" / "configs"
    registry.load(configs_dir)
    task = asyncio.create_task(_cleanup_draft_orders())
    law_task = asyncio.create_task(_law_monitor_loop())
    retry_task = asyncio.create_task(_auto_retry_loop())
    yield
    task.cancel()
    law_task.cancel()
    retry_task.cancel()


app = FastAPI(
    title="LawDocs API",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Некорректные данные запроса."})

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
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "situations_loaded": len(registry)}
