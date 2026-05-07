"""
Email-сервис: magic link и уведомления о заказе.
Использует aiosmtplib для async SMTP.
"""

import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send(to: str, subject: str, html: str, attachment_path: Path | None = None) -> None:
    if not settings.SMTP_HOST:
        logger.info("[EMAIL stub] To: %s | Subject: %s", to, subject)
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to

    msg.attach(MIMEText(html, "html", "utf-8"))

    if attachment_path and attachment_path.exists():
        data = attachment_path.read_bytes()
        part = MIMEApplication(data, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=attachment_path.name)
        msg.attach(part)

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


async def send_document_ready(email: str, order_id: str, pdf_path: Path | None = None) -> None:
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    html = f"""
    <p>Ваш документ готов!</p>
    <p>PDF прикреплён к этому письму. Также документ доступен по ссылке:</p>
    <p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        Открыть заказ
    </a></p>
    <p>Там вы найдёте Word и PDF версии, а также инструкцию — куда отправить документ и что приложить.</p>
    """
    await _send(
        to=email,
        subject="LawDocs — ваш документ готов",
        html=html,
        attachment_path=pdf_path,
    )


async def send_document_failed(email: str, order_id: str) -> None:
    html = f"""
    <p>К сожалению, при подготовке документа произошла ошибка.</p>
    <p>Мы уже получили уведомление и разбираемся. Напишите нам — вернём деньги или сформируем документ вручную.</p>
    <p>
      <a href="mailto:hi@lawdocs.ru" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
          Написать в поддержку
      </a>
    </p>
    <p style="color:#9ca3af;font-size:12px">Номер заказа: {order_id[:8].upper()}</p>
    """
    await _send(to=email, subject="LawDocs — ошибка при создании документа", html=html)
