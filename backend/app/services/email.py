"""
Email-сервис: magic link и уведомления о заказе.
Использует aiosmtplib для async SMTP.
"""

import asyncio
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send(
    to: str,
    subject: str,
    html: str,
    attachments: list[Path] | None = None,
) -> None:
    if not settings.SMTP_HOST:
        logger.info("[EMAIL stub] To: %s | Subject: %s", to, subject)
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to

    msg.attach(MIMEText(html, "html", "utf-8"))

    for path in (attachments or []):
        if path.exists():
            data = path.read_bytes()
            part = MIMEApplication(data, _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=path.name)
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
    html = f"""
    <p>Привет!</p>
    <p>Для входа в LawDocs нажмите кнопку ниже. Ссылка действует {settings.MAGIC_LINK_EXPIRE_MINUTES} минут.</p>
    <p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        Войти в LawDocs
    </a></p>
    <p style="color:#9ca3af;font-size:12px">Если вы не запрашивали вход — просто проигнорируйте это письмо.</p>
    """
    await _send(to=email, subject="Вход в LawDocs", html=html)


async def send_document_ready(
    email: str,
    order_id: str,
    pdf_path: Path | None = None,
    instruction_path: Path | None = None,
) -> None:
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    has_instruction = instruction_path and instruction_path.exists()
    attachments_note = (
        "К письму прикреплены претензия (PDF) и инструкция по подаче."
        if has_instruction
        else "К письму прикреплён PDF с претензией."
    )
    html = f"""
    <p>Ваш документ готов!</p>
    <p>{attachments_note} Также всё доступно по ссылке:</p>
    <p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        Открыть заказ
    </a></p>
    <p style="color:#6b7280;font-size:13px">Там же доступна версия в формате Word (.docx) для редактирования.</p>
    """
    attachments = [p for p in [pdf_path, instruction_path] if p]
    await _send(
        to=email,
        subject="LawDocs — ваш документ готов",
        html=html,
        attachments=attachments,
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
