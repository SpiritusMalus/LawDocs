import logging

import httpx

logger = logging.getLogger(__name__)


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
