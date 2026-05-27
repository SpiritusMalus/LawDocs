"""
Email-сервис: magic link и уведомления о заказе.
Использует aiosmtplib для async SMTP, Jinja2 для шаблонов писем.
"""

import asyncio
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent.parent / "templates" / "email"),
    autoescape=select_autoescape(["html"]),
)


async def _send(
    to: str,
    subject: str,
    html: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> None:
    if not settings.SMTP_HOST:
        logger.info("[EMAIL stub] To: %s | Subject: %s", to, subject)
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to

    msg.attach(MIMEText(html, "html", "utf-8"))

    for filename, data in (attachments or []):
        part = MIMEApplication(data, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    try:
        await asyncio.wait_for(
            aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
                start_tls=settings.SMTP_STARTTLS,
            ),
            timeout=10.0,
        )
        logger.info("Email sent successfully to %s", to)
    except asyncio.TimeoutError:
        logger.error("SMTP timeout sending to %s (10s exceeded)", to)
        raise
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, str(e))
        raise


async def send_magic_link(email: str, url: str) -> None:
    html = _templates.get_template("magic_link.html").render(
        url=url,
        expire_minutes=settings.MAGIC_LINK_EXPIRE_MINUTES,
    )
    await _send(to=email, subject="Вход в LawDocs", html=html)


async def send_document_ready(email: str, order_id: str) -> None:
    # Документ НЕ вкладываем в письмо: файлы доступны только в ЛК, где их можно
    # расшифровать ключом пользователя. Вложение положило бы открытый PDF в почту.
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    html = _templates.get_template("document_ready.html").render(url=url)
    await _send(to=email, subject="LawDocs — ваш документ готов", html=html)


async def send_document_failed(email: str, order_id: str) -> None:
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    html = _templates.get_template("document_failed.html").render(
        url=url,
        order_id=order_id[:8].upper(),
    )
    await _send(to=email, subject="LawDocs — ошибка при создании документа", html=html)


async def send_refund_notification(email: str, order_id: str) -> None:
    html = _templates.get_template("refund_notification.html").render(
        order_id=order_id[:8].upper(),
    )
    await _send(to=email, subject="LawDocs — возврат средств", html=html)
