"""
Email-сервис: magic link и уведомления о заказе.
Использует aiosmtplib для async SMTP.
"""

import asyncio
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


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
    # Документ НЕ вкладываем в письмо: файлы доступны только в ЛК, где их можно
    # расшифровать ключом пользователя. Вложение положило бы открытый PDF в почту.
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    html = f"""
    <p>Ваш документ готов!</p>
    <p>Претензия, инструкция по подаче и версия в формате Word доступны в личном кабинете:</p>
    <p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
        Открыть заказ
    </a></p>
    """
    await _send(to=email, subject="LawDocs — ваш документ готов", html=html)


async def send_document_failed(email: str, order_id: str) -> None:
    url = f"{settings.FRONTEND_URL}/orders/{order_id}"
    html = f"""
    <p>К сожалению, при подготовке документа произошла ошибка.</p>
    <p>Мы уже пробуем создать его повторно — обычно это занимает несколько минут.</p>
    <p>Если документ не появится в течение часа, нажмите «Попробовать ещё раз» в личном кабинете:</p>
    <p>
      <a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600">
          Перейти к заказу
      </a>
    </p>
    <p style="color:#9ca3af;font-size:12px">Номер заказа: {order_id[:8].upper()}</p>
    """
    await _send(to=email, subject="LawDocs — ошибка при создании документа", html=html)
