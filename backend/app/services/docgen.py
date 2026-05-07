"""
Генерация документов: .docx из python-docx (или docxtpl для шаблонов), .pdf через fpdf2.
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

_SAFE_SITUATION_ID = re.compile(r"^[a-z_]{1,64}$")
_SAFE_ORDER_ID = re.compile(r"^[0-9a-f\-]{36}$")


def _sanitize_situation_id(situation_id: str) -> str:
    if not _SAFE_SITUATION_ID.match(situation_id):
        raise ValueError(f"Invalid situation_id: {situation_id!r}")
    return situation_id


def _sanitize_order_id(order_id: str) -> str:
    if not _SAFE_ORDER_ID.match(order_id):
        raise ValueError(f"Invalid order_id: {order_id!r}")
    return order_id


def _find_template(situation_id: str, form_data: dict) -> Path | None:
    """Look for a .docx template: first by subtype, then by situation_id."""
    subtype = (
        form_data.get("problem_type")
        or form_data.get("violation_type")
        or form_data.get("incident_type")
    )
    if subtype:
        path = TEMPLATES_DIR / situation_id / f"{subtype}.docx"
        if path.exists():
            return path
    path = TEMPLATES_DIR / f"{situation_id}.docx"
    if path.exists():
        return path
    return None


def _render_template(template_path: Path, context: dict) -> bytes:
    """Render a docxtpl template with the given context."""
    from docxtpl import DocxTemplate

    tpl = DocxTemplate(str(template_path))
    tpl.render(context)
    buf = io.BytesIO()
    tpl.save(buf)
    return buf.getvalue()


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


def _instruction_to_pdf(content: str, legal_refs: list[dict]) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.add_font("FreeSans", fname="/usr/share/fonts/truetype/freefont/FreeSans.ttf")
    pdf.add_font("FreeSans", style="B", fname="/usr/share/fonts/truetype/freefont/FreeSansBold.ttf")
    pdf.set_margins(left=25, top=25, right=25)
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("FreeSans", style="B", size=13)
    pdf.multi_cell(0, 8, "Инструкция по подаче претензии")
    pdf.ln(4)

    # AI-generated content
    pdf.set_font("FreeSans", size=11)
    for para in content.split("\n"):
        if not para.strip():
            pdf.ln(3)
            continue
        pdf.multi_cell(0, 6, para)
        pdf.ln(1)

    if legal_refs:
        pdf.ln(6)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.get_x(), pdf.get_y(), 185, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("FreeSans", style="B", size=11)
        pdf.multi_cell(0, 6, "Полезные ссылки на законодательство:")
        pdf.ln(3)

        pdf.set_font("FreeSans", size=10)
        for ref in legal_refs:
            law = ref.get("law", "")
            url = ref.get("url", "")
            if not law or not url:
                continue
            pdf.set_text_color(0, 0, 0)
            pdf.write(6, f"• {law}:  ")
            pdf.set_text_color(0, 80, 200)
            pdf.write(6, "consultant.ru", link=url)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(7)

    return bytes(pdf.output())


async def generate_instruction(
    order_id: str,
    situation_id: str,
    content: str,
    legal_refs: list[dict],
) -> str:
    """Build instruction PDF, save to disk. Returns filename."""
    safe_sid = _sanitize_situation_id(situation_id)
    safe_oid = _sanitize_order_id(order_id)

    pdf_bytes = _instruction_to_pdf(content, legal_refs)

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"instrukciya_{safe_sid}_{date_str}.pdf"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_file, safe_oid, filename, pdf_bytes)

    return filename


async def generate_document(
    order_id: str,
    situation_id: str,
    content: str,
    form_data: dict | None = None,
) -> tuple[str, str]:
    """
    Builds .docx and .pdf, saves to local disk.
    If a .docx template exists for the situation, renders it via docxtpl (content = ai_narrative).
    Otherwise falls back to plain text → docx conversion.
    Returns (docx_filename, pdf_filename).
    """
    safe_sid = _sanitize_situation_id(situation_id)
    safe_oid = _sanitize_order_id(order_id)

    fd = form_data or {}
    template_path = _find_template(safe_sid, fd)

    if template_path:
        now = datetime.now(UTC)
        context = {
            **fd,
            "ai_narrative": content,
            "today": f"{now.day} {['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][now.month - 1]} {now.year} года",
        }
        docx_bytes = _render_template(template_path, context)
        logger.info("Rendered template %s for order %s", template_path.name, safe_oid)
    else:
        docx_bytes = _text_to_docx(content)

    pdf_bytes = _docx_to_pdf(docx_bytes)

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    docx_filename = f"pretenziya_{safe_sid}_{date_str}.docx"
    pdf_filename = f"pretenziya_{safe_sid}_{date_str}.pdf"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _write_file, safe_oid, docx_filename, docx_bytes)
    await loop.run_in_executor(None, _write_file, safe_oid, pdf_filename, pdf_bytes)

    return docx_filename, pdf_filename
