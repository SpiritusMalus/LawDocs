"""
Генерация документов: .docx из python-docx, .pdf через WeasyPrint.
Файлы сохраняются на локальный диск в DOCUMENTS_DIR/{order_id}/.
"""

import asyncio
import html
import io
import logging
import re
from pathlib import Path

from docx import Document as DocxDocument

from app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Допустимые символы в situation_id — защита от path traversal
_SAFE_SITUATION_ID = re.compile(r"^[a-z_]{1,32}$")


def _sanitize_situation_id(situation_id: str) -> str:
    if not _SAFE_SITUATION_ID.match(situation_id):
        raise ValueError(f"Invalid situation_id for storage: {situation_id!r}")
    return situation_id


def _text_to_docx(text: str) -> bytes:
    doc = DocxDocument()
    for paragraph in text.split("\n"):
        doc.add_paragraph(paragraph)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _docx_to_pdf(docx_bytes: bytes) -> bytes:
    from weasyprint import HTML
    import io as _io
    from docx import Document as DocxDoc

    doc_html = "<html><body style='font-family:Arial;font-size:12pt;padding:40px'>"
    doc = DocxDoc(_io.BytesIO(docx_bytes))
    for para in doc.paragraphs:
        doc_html += f"<p>{html.escape(para.text)}</p>"
    doc_html += "</body></html>"

    pdf_buf = _io.BytesIO()
    HTML(string=doc_html).write_pdf(pdf_buf)
    return pdf_buf.getvalue()


def _write_file(order_id: str, filename: str, data: bytes) -> None:
    docs_dir = Path(settings.DOCUMENTS_DIR) / order_id
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / filename).write_bytes(data)


def get_document_path(order_id: str, filename: str) -> Path:
    return Path(settings.DOCUMENTS_DIR) / order_id / filename


async def generate_document(order_id: str, situation_id: str, content: str) -> tuple[str, str]:
    """
    Builds .docx and .pdf from LLM content, saves to local disk.
    Returns (docx_filename, pdf_filename) stored under DOCUMENTS_DIR/{order_id}/.
    """
    safe_sid = _sanitize_situation_id(situation_id)
    docx_bytes = _text_to_docx(content)
    pdf_bytes = _docx_to_pdf(docx_bytes)

    docx_filename = f"{safe_sid}.docx"
    pdf_filename = f"{safe_sid}.pdf"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_file, order_id, docx_filename, docx_bytes)
    await loop.run_in_executor(None, _write_file, order_id, pdf_filename, pdf_bytes)

    return docx_filename, pdf_filename
