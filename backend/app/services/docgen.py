"""
Генерация документов: .docx из python-docx (или docxtpl для шаблонов), .pdf через fpdf2.
Файлы загружаются в Яндекс Object Storage (S3) по ключу {order_id}/{filename}.
"""

import asyncio
import io
import logging
import re
from datetime import datetime, UTC
from pathlib import Path

from docx import Document as DocxDocument

from app.services.storage import upload_bytes

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


def s3_key(order_id: str, filename: str) -> str:
    return f"{order_id}/{filename}"


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
    """Build instruction PDF, upload to S3. Returns S3 key."""
    safe_sid = _sanitize_situation_id(situation_id)
    safe_oid = _sanitize_order_id(order_id)

    pdf_bytes = await asyncio.get_running_loop().run_in_executor(
        None, _instruction_to_pdf, content, legal_refs
    )

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    filename = f"instrukciya_{safe_sid}_{date_str}.pdf"
    key = s3_key(safe_oid, filename)

    await upload_bytes(key, pdf_bytes)
    return key


async def generate_document(
    order_id: str,
    situation_id: str,
    content: str,
    form_data: dict | None = None,
) -> tuple[str, str]:
    """
    Builds .docx and .pdf, uploads to S3.
    Returns (docx_key, pdf_key).
    """
    safe_sid = _sanitize_situation_id(situation_id)
    safe_oid = _sanitize_order_id(order_id)

    fd = form_data or {}
    template_path = _find_template(safe_sid, fd)
    loop = asyncio.get_running_loop()

    if template_path:
        now = datetime.now(UTC)
        context = {
            **fd,
            "ai_narrative": content,
            "today": f"{now.day} {['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'][now.month - 1]} {now.year} года",
        }
        docx_bytes = await loop.run_in_executor(None, _render_template, template_path, context)
        logger.info("Rendered template %s for order %s", template_path.name, safe_oid)
    else:
        docx_bytes = await loop.run_in_executor(None, _text_to_docx, content)

    pdf_bytes = await loop.run_in_executor(None, _docx_to_pdf, docx_bytes)

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    docx_key = s3_key(safe_oid, f"pretenziya_{safe_sid}_{date_str}.docx")
    pdf_key = s3_key(safe_oid, f"pretenziya_{safe_sid}_{date_str}.pdf")

    await asyncio.gather(
        upload_bytes(docx_key, docx_bytes),
        upload_bytes(pdf_key, pdf_bytes),
    )

    return docx_key, pdf_key
