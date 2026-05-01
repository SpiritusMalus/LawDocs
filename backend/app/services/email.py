"""
Email-сервис: отправка magic link и уведомления о готовом документе.
Использует aiosmtplib для async SMTP.
"""

import logging

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send(to: str, subject: str, html: str) -> None:
    if not settings.SMTP_HOST:
        logger.info("[EMAIL stub] To: %s | Subject: %s", to, subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(html, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=True,
    )


async def send_magic_link(email: str, url: str) -> None:
    html = f"""
    <p>Привет!</p>
    <p>Для входа в LawDocs нажмите кнопку ниже. Ссылка действует {settings.MAGIC_LINK_EXPIRE_MINUTES} минут.</p>
    <p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        Войти в LawDocs
    </a></p>
    <p style="color:#9ca3af;font-size:12px">Если вы не запрашивали вход — просто проигнорируйте это письмо.</p>
    """
    await _send(to=email, subject="Вход в LawDocs", html=html)


async def send_document_ready(email: str, order_id: str) -> None:
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    html = f"""
    <p>Ваш документ готов!</p>
    <p>Перейдите по ссылке, чтобы скачать Word и PDF версии:</p>
    <p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        Скачать документ
    </a></p>
    <p>Там же вы найдёте инструкцию — куда отправить документ и что приложить.</p>
    """
    await _send(to=email, subject="LawDocs — ваш документ готов", html=html)
