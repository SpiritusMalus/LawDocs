"""
Watermarked-превью документа: растеризуем готовый PDF в PNG и наносим
диагональный водяной знак. Превью показывается ДО оплаты — текст в нём
неселектируемый (это растр), а чистый docx/pdf остаётся под gate'ом оплаты.

pymupdf (fitz) рендерит страницы PDF в пиксели; Pillow накладывает водяной знак
(диагональный поворот + альфа удобнее делать именно в Pillow).
"""

import io
import logging
from pathlib import Path

import fitz  # pymupdf
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_WATERMARK_TEXT = "ОБРАЗЕЦ · LawDocs · не для подачи"
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
_PREVIEW_DPI = 110


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _apply_watermark(img: Image.Image, text: str) -> None:
    """Накладывает плиточный диагональный полупрозрачный водяной знак (in place)."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(max(18, img.width // 28))

    bbox = draw.textbbox((0, 0), text, font=font)
    tile_w = bbox[2] - bbox[0]
    tile_h = bbox[3] - bbox[1]
    step_y = tile_h * 5
    step_x = tile_w + tile_w // 2

    y = -tile_h
    row = 0
    while y < img.height + tile_h:
        x = -tile_w + (row % 2) * (step_x // 2)
        while x < img.width + tile_w:
            draw.text((x, y), text, font=font, fill=(120, 120, 120, 70))
            x += step_x
        y += step_y
        row += 1

    rotated = overlay.rotate(30, resample=Image.BICUBIC, expand=False)
    img.paste(Image.alpha_composite(img.convert("RGBA"), rotated).convert("RGB"), (0, 0))


def render_watermarked_pngs(pdf_bytes: bytes, dpi: int = _PREVIEW_DPI) -> list[bytes]:
    """PDF → список PNG-байтов (по странице) с водяным знаком.

    Чисто CPU-bound и блокирующая операция — вызывать через executor.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages: list[bytes] = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            _apply_watermark(img, _WATERMARK_TEXT)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            pages.append(buf.getvalue())
        return pages
    finally:
        doc.close()
