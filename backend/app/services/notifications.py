import logging

import httpx

logger = logging.getLogger(__name__)


def format_order_alert(
    kind: str,
    *,
    order_id: str,
    situation_id: str,
    user_email: str,
    payment_id: str | None = None,
    refunded: bool | None = None,
) -> str:
    """Собирает текст Telegram-алерта по заказу.

    kind: "refund" — авто-возврат при провале генерации;
          "watchdog_refund" — возврат по watchdog (зависший generating);
          "failed" — генерация провалилась без возврата.
    Тексты сохранены дословно (эмодзи, формат HTML) для консистентности
    с историей алертов.
    """
    if kind in ("refund", "watchdog_refund"):
        title = "Auto-refund" if kind == "refund" else "Watchdog auto-refund"
        status_word = "OK" if refunded else "FAILED"
        return (
            f"💸 <b>{title} {status_word}</b>\n"
            f"order_id: <code>{order_id}</code>\n"
            f"payment_id: <code>{payment_id}</code>\n"
            f"situation: {situation_id}\n"
            f"email: {user_email}"
        )
    return (
        f"❌ <b>Order failed</b>\n"
        f"order_id: <code>{order_id}</code>\n"
        f"situation: {situation_id}\n"
        f"email: {user_email}"
    )


async def send_telegram_alert(message: str) -> None:
    from app.core.config import settings

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            )
    except Exception:
        logger.exception("Failed to send Telegram alert")
