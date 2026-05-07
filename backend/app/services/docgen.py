"""
Генерация документов: .docx из python-docx, .pdf через WeasyPrint.
Файлы сохраняются на локальный диск в DOCUMENTS_DIR/{order_id}/.
"""

import asyncio
import io
import logging
import re
from datetime import datetime, UTC
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
    import io as _io
    from docx import Document as DocxDoc
    from fpdf import FPDF

    doc = DocxDoc(_io.BytesIO(docx_bytes))

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.add_font("FreeSans", fname="/usr/share/fonts/truetype/freefont/FreeSans.ttf")
    pdf.set_font("FreeSans", size=11)
    pdf.set_margins(left=25, top=25, right=25)
    pdf.set_auto_page_break(auto=True, margin=20)

    for para in doc.paragraphs:
        text = para.text
        if not text.strip():
            pdf.ln(4)
            continue
        pdf.multi_cell(0, 6, text)
        pdf.ln(1)

    return bytes(pdf.output())


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

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    docx_filename = f"pretenziya_{safe_sid}_{date_str}.docx"
    pdf_filename = f"pretenziya_{safe_sid}_{date_str}.pdf"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_file, order_id, docx_filename, docx_bytes)
    await loop.run_in_executor(None, _write_file, order_id, pdf_filename, pdf_bytes)

    return docx_filename, pdf_filename
