"""
Генерация 32 PDF-образцов через прод-пайплайн генерации текста (fill_template:
GigaChat → проверка YandexGPT), fpdf2 рисует PDF с водяным знаком «ОБРАЗЕЦ».
Запуск: cd backend && source .venv/bin/activate && python3 ../scripts/gen_samples.py
        (опционально --only id1,id2)
"""
import asyncio
import sys
import yaml
from fpdf import FPDF
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.core.config import settings
from app.services.docgen import _render_right_block, _render_sig_block, _split_last_line
from app.services.llm import fill_template

ROOT      = Path(__file__).parent.parent
DATA_FILE = Path(__file__).parent / "sample_fake_data.yaml"
OUT_DIR   = ROOT / "frontend" / "public" / "samples"
ARIAL     = "/Library/Fonts/Arial Unicode.ttf"
ARIAL_B   = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


# ── PDF ───────────────────────────────────────────────────────

class _SamplePDF(FPDF):
    """FPDF с footer-дисклеймером на каждой странице."""

    def footer(self) -> None:
        self.set_y(-(self.b_margin))
        self.set_draw_color(180, 180, 180)
        self.line(25, self.get_y() - 2, 190, self.get_y() - 2)
        self.set_font("A", size=8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 4, "Образец. Не является юридической консультацией. "
                        "Персональные данные вымышлены. law-docs.ru", align="L")
        self.set_text_color(0, 0, 0)


def make_pdf(
    header: list[str],
    title: str,
    body: str,
    out_path: Path,
) -> None:
    pdf = _SamplePDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("A",          fname=ARIAL)
    pdf.add_font("A", style="B", fname=ARIAL_B)
    pdf.set_margins(left=25, top=25, right=20)
    # margin=25 оставляет место для footer (~10мм) + подпись (~15мм)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    # watermark
    pdf.set_font("A", style="B", size=58)
    pdf.set_text_color(225, 225, 225)
    with pdf.rotation(42, x=105, y=148):
        pdf.text(x=35, y=163, text="ОБРАЗЕЦ")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("A", size=11)

    if header:
        _render_right_block(pdf, header)
        pdf.ln(4)

    if title:
        pdf.set_font("A", style="B", size=12)
        pdf.multi_cell(0, 7, title, align="C")
        pdf.set_font("A", size=11)
        pdf.ln(4)

    # Последняя строка тела рендерится атомарно с блоком подписи
    # (keep-with-last-line), чтобы подпись не уезжала на новую страницу одна.
    lines = body.split("\n")
    head_lines, tail_line = _split_last_line(lines)
    for line in head_lines:
        if not line.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 6, line)
            pdf.ln(1)

    _render_sig_block(pdf, tail_line=tail_line)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))


# ── main ──────────────────────────────────────────────────────

async def main() -> None:
    only = set()
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        only = set(sys.argv[idx + 1].split(","))

    if not settings.GIGACHAT_AUTH_KEY and not (settings.YANDEX_API_KEY and settings.YANDEX_FOLDER_ID):
        print("❌  Не настроен ни GigaChat, ни YandexGPT в backend/.env")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        situations = yaml.safe_load(f)
    if only:
        situations = [s for s in situations if s["_id"] in only]

    print(f"Генерируем {len(situations)} документов через прод-пайплайн (GigaChat → YandexGPT).\n")

    for sit in situations:
        sid      = sit["_id"]
        filename = sit["_filename"]
        form_data = {k: v for k, v in sit.items() if not k.startswith("_")}

        async def _generate_one(fd: dict) -> tuple[str, str, str]:
            # Прод-пайплайн: enrich + hybrid/full + YandexGPT review + post-substitute + cleanup
            body, header, title = await fill_template(sid, fd)
            if "--debug" in sys.argv:
                print(f"\n--- BODY ({sid}) ---\n{body[:400]}\n")
            return header, title, body

        print(f"⏳  {sid}…", end=" ", flush=True)
        try:
            header, title, body = await _generate_one(form_data)
            make_pdf(header, title, body, OUT_DIR / filename)
            print(f"✓  {filename}")
        except Exception as e:
            print(f"\n    ⚠  ошибка ({e!r}), повтор через 3с…", flush=True)
            await asyncio.sleep(3)
            try:
                header, title, body = await _generate_one(form_data)
                make_pdf(header, title, body, OUT_DIR / filename)
                print(f"✓  {filename}  (retry)")
            except Exception as e2:
                print(f"❌  {sid}: {e2!r}")

    print("\nГотово → frontend/public/samples/")


if __name__ == "__main__":
    asyncio.run(main())
