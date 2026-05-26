"""
Генерация 25 PDF-образцов: GigaChat генерирует текст, fpdf2 рисует PDF.
Запуск: cd backend && source .venv/bin/activate && python3 ../scripts/gen_samples.py
"""
import asyncio
import os
import re
import uuid
import yaml
import httpx
from fpdf import FPDF
from pathlib import Path

ROOT       = Path(__file__).parent.parent
ENV_FILE   = ROOT / "backend" / ".env"
DATA_FILE  = Path(__file__).parent / "sample_fake_data.yaml"
OUT_DIR    = ROOT / "frontend" / "public" / "samples"
CONFIGS    = ROOT / "backend" / "app" / "situations" / "configs"
ARIAL      = "/Library/Fonts/Arial Unicode.ttf"
ARIAL_B    = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
GIGA_AUTH  = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGA_API   = "https://gigachat.devices.sberbank.ru/api/v1"

# Правила форматирования — добавляются к каждому system_prompt
FORMAT_RULES = """
ПРАВИЛА ФОРМАТИРОВАНИЯ — строго обязательны:

1. Выводи ТОЛЬКО готовый текст документа. Никаких пояснений, предисловий, комментариев, вступлений от себя.

1а. НЕ пиши нигде в документе дату его составления в любом формате («сегодня», «18 мая 2026 года», «29.04.2026», «на дату подачи», «на текущую дату» и т.д.) — дату заявитель впишет от руки при подписании. Используй только даты событий из данных формы (дата покупки, дата нарушения и т.п.). Пункт «Дата и подпись» в инструкции означает, что это место для бланка — НЕ выводи ни дату, ни подпись, ни метку «Дата и подпись».

2. НЕ выводи метки разделов в тексте: «Шапка:», «Заголовок:», «Описание:», «Нарушение:», «Обстоятельства:», «Правовое обоснование:», «Требование:», «Дата и подпись», «Подпись:», «Расчёт компенсации:», «Расчёт:», «Кредитор:», «Приложения:», «Приложение:», «Коллекторская организация:», «Долг по договору:», «Основание несогласия», «Дополнительные обстоятельства» и любые подобные заголовки внутри документа. Пиши сразу содержание без метки.

2а. НЕ пиши первым абзацем после заголовка документа вводное предложение типа «Прошу рассмотреть мою претензию по вопросу...», «Настоящей претензией уведомляю...», «о возврате денежных средств за...». Сразу начинай с фактов: когда, что произошло, договор и т.д.

2б. НЕ пиши город и дату составления документа отдельными строками после заголовка («г. Москва», «01 июня 2026 г.» и т.п.) — дату заявитель впишет от руки при подписании.

3. НЕ используй markdown: никаких **жирный**, *курсив*, # заголовки, --- линии.

4. НЕ пиши текст ЗАГЛАВНЫМИ буквами нигде в документе, включая ФИО, расчёты, итоги, требования и любые другие части. Единственное исключение — само название документа (ПРЕТЕНЗИЯ / ЖАЛОБА / ВОЗРАЖЕНИЕ / ЗАЯВЛЕНИЕ / УВЕДОМЛЕНИЕ), оно пишется отдельной строкой заглавными без кавычек. Запрещено: «ИТОГО К ВЫПЛАТЕ», «ПРОШУ ВАС ВЫПЛАТИТЬ», «ТРЕБУЮ», «В СВЯЗИ С ВЫШЕИЗЛОЖЕННЫМ», «ПРАВОВОЕ», «РУКОВОДИТЕЛЮ», «ОТ:» и любые подобные — всё обычным регистром с заглавной буквы. В шапке пиши «Руководителю» и «От:» строчными.

4а. Заголовок документа (ПРЕТЕНЗИЯ / ЖАЛОБА / и т.д.) пишется одним словом без каких-либо пояснений, описаний, скобок или подзаголовков. НЕ пиши «ПРЕТЕНЗИЯ о возврате», «ПРЕТЕНЗИЯ (о перерасчёте)», «ЖАЛОБА на действия» — только одно слово.

5. НЕ упоминай имена переменных и кодовые значения из формы (violation_type, night_calls, has_photo, problem_type, damage_claim и т.д.) — применяй их смысл по-русски.

6. НЕ пиши условную логику («если X = Y», «Если has_photo = yes:»). Просто применяй её молча.

7. НЕ заключай в квадратные скобки даты, имена, адреса и любые данные — они уже известны из формы, пиши их напрямую. Если в инструкции встречается [field_name] — подставь реальное значение из данных, не выводи скобки.

8. Используй только длинное тире (—). НЕ двойное тире (--).

9. Блок подписи — строго такой формат, без вариаций:

   _________________ / _________________

   НЕ печатай дату — человек впишет её от руки.
   НЕ печатай ФИО или инициалы — расшифровку человек впишет от руки.
   НЕ пиши слово «Подпись:», «Расшифровка:» или «Дата:» перед линиями.

10. ОБЯЗАТЕЛЬНЫЙ ПОРЯДОК ДОКУМЕНТА (строго соблюдать):
    — СНАЧАЛА: шапка (кому и от кого) — реквизиты получателя и отправителя, каждый с новой строки
    — ЗАТЕМ: заголовок (ПРЕТЕНЗИЯ / ЖАЛОБА / ЗАЯВЛЕНИЕ) — отдельной строкой
    — ЗАТЕМ: основной текст
    — В КОНЦЕ: дата + блок подписи
    НЕ меняй этот порядок. НЕ дублируй получателя.

11. Блок подписи — обе части (подпись и расшифровка) на ОДНОЙ строке:
    _________________ / _________________
    — НЕ разноси их на разные строки.
    — НЕ печатай никакого ФИО — ни до, ни после этой строки.
"""


# ── helpers ───────────────────────────────────────────────────

def load_env(path: Path) -> dict:
    env = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


def find_situation_config(situation_id: str) -> dict:
    for f in CONFIGS.rglob("*.yaml"):
        d = yaml.safe_load(f.read_text())
        if d.get("id") == situation_id:
            return d
    return {}


def find_system_prompt(situation_id: str) -> str:
    return find_situation_config(situation_id).get("system_prompt", "")


# Алиасы: ключи из system_prompt → ключи из YAML-данных
_FIELD_ALIASES: dict[str, list[str]] = {
    "full_name":       ["user_full_name", "full_name"],
    "contact_address": ["user_address", "contact_address"],
    "phone":           ["user_phone", "phone"],
    "email":           ["user_email", "email"],
    "name":            ["user_full_name", "full_name", "name"],
    "address":         ["user_address", "contact_address", "address"],
}


def pre_substitute_prompt(system_prompt: str, form_data: dict) -> str:
    """Подставляет реальные значения вместо [field_name] в system_prompt."""
    def replacer(m: re.Match) -> str:
        key = m.group(1)
        if key in form_data and form_data[key]:
            return str(form_data[key])
        for alias_key, candidates in _FIELD_ALIASES.items():
            if key == alias_key:
                for candidate in candidates:
                    if candidate in form_data and form_data[candidate]:
                        return str(form_data[candidate])
        return m.group(0)  # оставляем как есть, если значение не найдено
    return re.sub(r"\[([a-z_]+)\]", replacer, system_prompt)


def build_user_prompt(situation_id: str, form_data: dict) -> str:
    lines = [f"Ситуация: {situation_id}", "", "Данные:"]
    for k, v in form_data.items():
        if v is not None and str(v).strip():
            lines.append(f"- {k}: {str(v)[:800]}")
    return "\n".join(lines)


# ── Hybrid-mode calculator (для ситуаций с python_template) ──

from datetime import date as _date
from decimal import Decimal as _Decimal, ROUND_HALF_UP as _ROUND_HALF_UP

_MONTHS_GENITIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

_DDU_TERMINATION_REASON_TEXTS = {
    # Творительный падеж — используется после «в связи с»
    "delay_2months": (
        "нарушением предусмотренного договором срока передачи объекта долевого "
        "строительства более чем на два месяца (п. 1 ч. 1 ст. 9 Федерального закона № 214-ФЗ)"
    ),
    "defects_major": (
        "существенным нарушением требований к качеству объекта долевого "
        "строительства (п. 2 ч. 1 ст. 9 Федерального закона № 214-ФЗ)"
    ),
    "construction_stopped": (
        "прекращением или приостановлением строительства многоквартирного дома "
        "при наличии обстоятельств, очевидно свидетельствующих о том, что в "
        "предусмотренный договором срок объект долевого строительства не будет "
        "передан участнику долевого строительства "
        "(п. 3 ч. 1 ст. 9 Федерального закона № 214-ФЗ)"
    ),
    "other": "",
}


def _parse_date_any(value) -> "_date | None":
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _fmt_date_ru(d: "_date") -> str:
    return f"{d.day} {_MONTHS_GENITIVE[d.month - 1]} {d.year} года"


def enrich_ddu_termination(form_data: dict) -> dict:
    """Обогащает form_data вычисленными полями для гибридного шаблона ddu_termination."""
    data = dict(form_data)

    reason_code = str(data.get("termination_reason", ""))
    data["termination_reason_text"] = _DDU_TERMINATION_REASON_TEXTS.get(reason_code, reason_code)

    cd = _parse_date_any(data.get("contract_date"))
    pd_ = _parse_date_any(data.get("payment_date"))
    if cd:
        data["formatted_contract_date"] = _fmt_date_ru(cd)
    if pd_:
        data["formatted_payment_date"] = _fmt_date_ru(pd_)

    # Пересчитываем финансы (либо берём из fake data если уже заданы)
    if pd_ and not data.get("calculated_days_used"):
        days = max((_date.today() - pd_).days, 0)
        try:
            price = _Decimal(str(data["contract_price"]))
            rate = _Decimal(str(data["cb_rate"]))
            interest = price * rate / _Decimal("100") / _Decimal("150") * _Decimal(days)
            total = price + interest
            data["calculated_days_used"] = str(days)
            data["calculated_interest"] = str(
                interest.quantize(_Decimal("0.01"), rounding=_ROUND_HALF_UP)
            )
            data["calculated_total_return"] = str(
                total.quantize(_Decimal("0.01"), rounding=_ROUND_HALF_UP)
            )
        except Exception:
            pass

    return data


# Реестр гибридных обогатителей: situation_id → функция
_HYBRID_ENRICHERS = {
    "ddu_termination": enrich_ddu_termination,
}


# ── GigaChat ──────────────────────────────────────────────────

async def get_token(auth_key: str) -> str:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            GIGA_AUTH,
            headers={"Authorization": f"Basic {auth_key}",
                     "RqUID": str(uuid.uuid4()),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"scope": "GIGACHAT_API_PERS"}, timeout=15,
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def call_giga(token: str, system_prompt: str, user_prompt: str) -> str:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            f"{GIGA_API}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={"model": "GigaChat",
                  "messages": [{"role": "system", "content": system_prompt},
                                {"role": "user",   "content": user_prompt}],
                  "temperature": 0.2, "max_tokens": 4096},
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ── Детектор отказа GigaChat ──────────────────────────────────

_REFUSAL_MARKERS = [
    "временно ограничены",
    "языковая модель",
    "генеративные языковые модели",
    "не могу помочь",
    "не могу выполнить",
    "не могу составить",
    "не предоставляю консультации",
    "не предоставляю юридические",
    "не могу дать медицинские",
    "чувствительные темы",
    "ограничены разговоры",
    "не обладают собственным мнением",
]


def _is_refusal(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _REFUSAL_MARKERS)


# ── PDF helpers ───────────────────────────────────────────────

_TITLE_WORDS = {"ПРЕТЕНЗИЯ", "ЖАЛОБА", "ВОЗРАЖЕНИЕ", "ЗАЯВЛЕНИЕ", "ХОДАТАЙСТВО", "УВЕДОМЛЕНИЕ"}
_DATE_RE = re.compile(
    r"^\s*\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|"
    r"июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*года\s*$",
    re.IGNORECASE,
)
_SIG_RE        = re.compile(r"_{4,}")
_DATE_SHORT_RE = re.compile(r"^\s*\d{1,2}\.\d{2}\.\d{4}\s*$")


def _split_document(lines: list[str]) -> tuple[list[str], str, list[str], list[str]]:
    """Делит строки документа на (шапка, заголовок, тело, блок_подписи)."""
    # Ищем заголовок — строка только из заглавных букв, входит в TITLE_WORDS
    title_idx: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in _TITLE_WORDS or any(stripped.startswith(t + " ") for t in _TITLE_WORDS):
            title_idx = i
            break

    # Ищем начало блока подписи: линия подчёркиваний ИЛИ дата (любого формата)
    # в последних 14 строках
    sig_start: int | None = None
    search_from = max(0, len(lines) - 14)
    for i in range(search_from, len(lines)):
        if (_SIG_RE.search(lines[i])
                or _DATE_RE.search(lines[i])
                or _DATE_SHORT_RE.match(lines[i])
                or lines[i].strip().lower().startswith("дата и подпись")):
            sig_start = i
            break

    if title_idx is not None:
        header = lines[:title_idx]
        title  = lines[title_idx].strip()
        after  = lines[title_idx + 1:]
    else:
        header = []
        title  = ""
        after  = lines

    if sig_start is not None:
        # sig_start относительно исходного lines; пересчитываем для after
        body_end = (sig_start - (title_idx + 1 if title_idx is not None else 0))
        body = after[:body_end]
        sig  = after[body_end:]
    else:
        body = after
        sig  = []

    # Убираем хвостовые пустые строки из тела — иначе они создают gap перед подписью
    while body and not body[-1].strip():
        body.pop()

    return header, title, body, sig


def _render_right_block(pdf: "FPDF", lines: list[str], line_h: float = 5.5) -> None:
    """Рендерит блок строк в правой колонке (x=105, w=85)."""
    RIGHT_X = 105.0
    RIGHT_W = 85.0
    for line in lines:
        if not line.strip():
            pdf.ln(2)
        else:
            pdf.set_x(RIGHT_X)
            pdf.multi_cell(RIGHT_W, line_h, line.strip(), align="L")


def _render_sig_block(pdf: "FPDF", sig_lines: list[str], line_h: float = 6.0) -> None:
    """Блок подписи: дата-бланк слева + подпись/расшифровка-бланк справа. Всё от руки."""
    PAGE_W  = 210.0
    LEFT_M  = 25.0
    RIGHT_M = 20.0
    BODY_W  = PAGE_W - LEFT_M - RIGHT_M
    SIG_W   = 80.0

    if pdf.get_y() + 20 > pdf.h - pdf.b_margin:
        pdf.add_page()

    DATE_TEXT = "«___» _________________ 20___ г."
    SIG_TEXT  = "_________________ / _________________"

    pdf.ln(6)
    pdf.set_x(LEFT_M)
    pdf.cell(BODY_W - SIG_W, line_h, DATE_TEXT)
    pdf.set_x(LEFT_M + BODY_W - SIG_W)
    pdf.cell(SIG_W, line_h, SIG_TEXT)
    pdf.ln(line_h)


# ── PDF renderer ──────────────────────────────────────────────

def make_pdf(text: str, out_path: Path) -> None:
    # Постобработка: двойное тире → длинное тире
    text = re.sub(r'(?<!\-)\-\-(?!\-)', '—', text)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("A",          fname=ARIAL)
    pdf.add_font("A", style="B", fname=ARIAL_B)
    pdf.set_margins(left=25, top=25, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # watermark
    pdf.set_font("A", style="B", size=58)
    pdf.set_text_color(225, 225, 225)
    with pdf.rotation(42, x=105, y=148):
        pdf.text(x=35, y=163, text="ОБРАЗЕЦ")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("A", size=11)

    lines = text.split("\n")
    header, title, body, sig = _split_document(lines)

    # 1. Шапка — правый верхний угол
    if header:
        _render_right_block(pdf, header)
        pdf.ln(4)

    # 2. Заголовок — по центру
    if title:
        pdf.set_font("A", style="B", size=12)
        pdf.multi_cell(0, 7, title, align="C")
        pdf.set_font("A", size=11)
        pdf.ln(4)

    # 3. Тело — слева
    for line in body:
        if not line.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 6, line)
            pdf.ln(1)

    # 4. Блок подписи — справа, не режется переносом страницы
    if sig:
        _render_sig_block(pdf, sig)
    pdf.ln(6)

    # disclaimer
    y = pdf.get_y() + 2
    pdf.set_draw_color(180, 180, 180)
    pdf.line(25, y, 190, y)
    pdf.set_y(y + 3)
    pdf.set_font("A", size=8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5, "Образец. Не является юридической консультацией. "
                            "Персональные данные вымышлены. law-docs.ru")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))


# ── main ──────────────────────────────────────────────────────

async def main() -> None:
    import sys
    only = set()
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        only = set(sys.argv[idx + 1].split(","))

    env = load_env(ENV_FILE)
    auth_key = env.get("GIGACHAT_AUTH_KEY", "")
    if not auth_key:
        print("❌  GIGACHAT_AUTH_KEY не найден в backend/.env")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        situations = yaml.safe_load(f)
    if only:
        situations = [s for s in situations if s["_id"] in only]

    print("Получаем токен GigaChat…")
    token = await get_token(auth_key)
    print(f"✓  Токен получен. Генерируем {len(situations)} документов.\n")

    for sit in situations:
        sid      = sit["_id"]
        filename = sit["_filename"]
        config   = find_situation_config(sid)
        if not config:
            print(f"⚠  конфиг не найден для {sid}")
            continue

        form_data = {k: v for k, v in sit.items() if not k.startswith("_")}

        print(f"⏳  {sid}…", end=" ", flush=True)
        try:
            python_template = config.get("python_template")
            if python_template:
                # Гибридный режим: LLM перефразирует только нарратив клиента
                if sid in _HYBRID_ENRICHERS:
                    form_data = _HYBRID_ENRICHERS[sid](form_data)

                narrative_fields = config.get("narrative_fields", [])
                narrative_prompt = config.get("narrative_prompt", "")
                raw_narrative = " ".join(
                    str(form_data.get(f, "")) for f in narrative_fields if form_data.get(f)
                )
                if raw_narrative and narrative_prompt:
                    polished = await call_giga(
                        token, narrative_prompt, f"Исправь и перефразируй: {raw_narrative}"
                    )
                    if _is_refusal(polished):
                        print(f"⚠  LLM отказала перефразировать нарратив — используем сырой текст")
                        polished = raw_narrative
                else:
                    polished = raw_narrative

                text = pre_substitute_prompt(python_template, form_data)
                text = text.replace("{{llm_narrative}}", polished)
            else:
                # Стандартный режим: LLM генерирует весь документ
                sp = config.get("system_prompt", "")
                if not sp:
                    print(f"⚠  system_prompt не найден для {sid}")
                    continue
                sp = FORMAT_RULES + "\n" + pre_substitute_prompt(sp, form_data)
                up = build_user_prompt(sid, form_data)
                text = await call_giga(token, sp, up)
                if _is_refusal(text):
                    print(f"🚫  GigaChat отказал (content filter): пропускаем {filename}")
                    print(f"    Ответ: {text[:200]!r}")
                    continue
                if len(text.strip()) < 200:
                    print(f"⚠  GigaChat вернул слишком короткий текст ({len(text.strip())} симв.): пропускаем {filename}")
                    print(f"    Ответ: {text[:300]!r}")
                    continue

            make_pdf(text, OUT_DIR / filename)
            print(f"✓  {filename}")
        except Exception as e:
            print(f"❌  {e}")

    print(f"\nГотово → frontend/public/samples/")


if __name__ == "__main__":
    asyncio.run(main())
