"""
Генерация документов: .docx из python-docx, .pdf через WeasyPrint.
Файлы загружаются в S3-совместимое хранилище (Selectel / Timeweb).
"""

import io
import logging
from pathlib import Path

from docx import Document as DocxDocument

from app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _text_to_docx(text: str) -> bytes:
    doc = DocxDocument()

    # Стиль Normal уже есть в шаблоне по умолчанию
    for paragraph in text.split("\n"):
        doc.add_paragraph(paragraph)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _docx_to_pdf(docx_bytes: bytes) -> bytes:
    """
    Конвертация .docx → .pdf через WeasyPrint.
    В проде лучше использовать LibreOffice headless для точного рендера,
    но WeasyPrint не требует системных зависимостей на Selectel.
    """
    from weasyprint import HTML  # импорт здесь — тяжёлая зависимость

    # WeasyPrint работает с HTML — конвертируем текст в простой HTML
    html = "<html><body style='font-family:Arial;font-size:12pt;padding:40px'>"
    from docx import Document as DocxDoc
    import io as _io
    doc = DocxDoc(_io.BytesIO(docx_bytes))
    for para in doc.paragraphs:
        html += f"<p>{para.text}</p>"
    html += "</body></html>"

    pdf_buf = _io.BytesIO()
    HTML(string=html).write_pdf(pdf_buf)
    return pdf_buf.getvalue()


async def _upload_to_s3(key: str, data: bytes, content_type: str) -> None:
    """Простая PUT-загрузка в S3 через httpx (без boto3 — меньше зависимостей)."""
    if not settings.S3_ENDPOINT:
        logger.warning("S3 not configured — skipping upload for key %s", key)
        return

    # TODO: реализовать SigV4-подпись при переходе к проду
    logger.info("Would upload %s bytes to s3://%s/%s", len(data), settings.S3_BUCKET, key)


async def _get_presigned_url(key: str) -> str:
    """Возвращает временную ссылку для скачивания файла из S3."""
    if not settings.S3_ENDPOINT:
        return f"/dev/documents/{key}"
    # TODO: реализовать SigV4 presigned URL
    return f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"


async def generate_document(order_id: str, situation_id: str, content: str) -> tuple[str, str]:
    """
    Собирает .docx и .pdf из LLM-контента, загружает в S3.
    Возвращает (docx_key, pdf_key).
    """
    docx_bytes = _text_to_docx(content)
    pdf_bytes = _docx_to_pdf(docx_bytes)

    docx_key = f"documents/{order_id}/{situation_id}.docx"
    pdf_key = f"documents/{order_id}/{situation_id}.pdf"

    await _upload_to_s3(docx_key, docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    await _upload_to_s3(pdf_key, pdf_bytes, "application/pdf")

    return docx_key, pdf_key


async def get_presigned_urls(docx_key: str, pdf_key: str) -> tuple[str, str]:
    return await _get_presigned_url(docx_key), await _get_presigned_url(pdf_key)
