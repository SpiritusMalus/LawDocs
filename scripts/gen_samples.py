"""
Генерация 25 PDF-образцов: GigaChat генерирует текст, fpdf2 рисует PDF.
Запуск: cd backend && source .venv/bin/activate && python3 ../scripts/gen_samples.py
"""
import asyncio
import os
import re
import sys
import uuid
import yaml
import httpx
from fpdf import FPDF
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.services.text_cleanup import clean_llm_text, fix_dashes, has_quality_artifacts
from app.services.docgen import _build_header, _render_right_block, _render_sig_block
from app.services.llm import _parse_body_json

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
ПРАВИЛА — строго обязательны:

1. Выводи ТОЛЬКО готовый текст документа. Никаких пояснений, предисловий, комментариев от себя.

2. ОБЯЗАТЕЛЬНЫЙ ПОРЯДОК (строго соблюдать): сначала шапка (кому / от кого), ЗАТЕМ заголовок документа одним словом (ПРЕТЕНЗИЯ / ЖАЛОБА / ЗАЯВЛЕНИЕ / ВОЗРАЖЕНИЕ / УВЕДОМЛЕНИЕ), ЗАТЕМ основной текст. ЗАПРЕЩЕНО писать заголовок до шапки.

3. Шапка: «Руководителю [получатель]» и «От: [ФИО, адрес, телефон, email]» — каждый реквизит с новой строки. Не дублируй получателя в тексте.

4. Заголовок — одно слово заглавными, без пояснений и подзаголовков. Не пиши после заголовка город или дату или какой-либо текст.

5. Основной текст — сразу с фактов (когда, что, договор). Не начинай с «Прошу рассмотреть», «Настоящей претензией» и подобных вступлений.

6. Текст — обычный регистр везде кроме заголовка. Не пиши ЗАГЛАВНЫМИ слова внутри текста.

7. Не упоминай названия переменных формы (violation_type, has_photo и т.п.) — применяй их смысл по-русски молча.

8. НЕ пиши квадратные скобки — подставляй значения из данных напрямую.

9. Не используй markdown (**жирный**, *курсив*, # заголовки).

10. Используй ТОЛЬКО длинное тире (—). Одинарный дефис (-) как пауза или в перечислениях — ЗАПРЕЩЁН. ЗАПРЕЩЕНО двойное тире (--).

11. Дату и подпись не выводи — они добавляются автоматически.

12. Аббревиатуры организационно-правовых форм — ВСЕГДА заглавными буквами: ООО, АО, ПАО, ГБУ, МБУ, ИП, ФГУП, МУП. Например: «ООО «Стройгрупп»», «АО «Альфа-Банк»», «ГБУ «Жилищник»» — никогда не «ооо» или «Ооо».
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


_RETRY_FEEDBACK = (
    "\n\nВАЖНО: предыдущий ответ содержал ошибки форматирования. Повтори, строго соблюдая правила:\n"
    "- НЕ пиши метки разделов ни с номером, ни без: «Шапка:», «Описание:», «Требование:», «Нарушение:», «Расчёт:», «Предупреждение:», «Реквизиты:» и любые подобные — пиши сразу содержание без метки\n"
    "- НЕ пиши условные конструкции («Если X = Y», «если указан...», «если есть...») — просто применяй их молча\n"
    "- НЕ пиши дату составления документа\n"
    "- НЕ пиши 'Дата и подпись'\n"
    "- НЕ используй **жирный** или *курсив*\n"
    "- НЕ пиши слова ЗАГЛАВНЫМИ БУКВАМИ внутри текста (кроме названия документа)\n"
    "- Заголовок документа — одно слово без пояснений: ПРЕТЕНЗИЯ (не 'ПРЕТЕНЗИЯ о возврате...')"
)


def _has_quality_artifacts(text: str) -> bool:
    if len(text.strip()) < 300:
        return True
    return has_quality_artifacts(text)


async def _call_once(token: str, system_prompt: str, user_prompt: str) -> str:
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


async def call_giga(token: str, system_prompt: str, user_prompt: str, *, validate: bool = False) -> str:
    text = await _call_once(token, system_prompt, user_prompt)
    if validate:
        for attempt in range(1, 3):
            if not _has_quality_artifacts(text):
                break
            print(f"    ⚠  артефакты форматирования (попытка {attempt}), повтор…")
            text = await _call_once(token, system_prompt, user_prompt + _RETRY_FEEDBACK)
    return text


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

_DOC_TYPE_TITLES = {
    "pretenziya": "ПРЕТЕНЗИЯ",
    "zhaloba": "ЖАЛОБА",
    "zayavlenie": "ЗАЯВЛЕНИЕ",
    "vozrazhenie": "ВОЗРАЖЕНИЕ",
    "hodatajstvo": "ХОДАТАЙСТВО",
    "uvedomlenie": "УВЕДОМЛЕНИЕ",
}


# ── Постобработка текста LLM ──────────────────────────────────
# (all patterns and functions moved to app.services.text_cleanup)


# ── PDF renderer ──────────────────────────────────────────────

def make_pdf(
    header: list[str],
    title: str,
    body: str,
    out_path: Path,
) -> None:
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

    if header:
        _render_right_block(pdf, header)
        pdf.ln(4)

    if title:
        pdf.set_font("A", style="B", size=12)
        pdf.multi_cell(0, 7, title, align="C")
        pdf.set_font("A", size=11)
        pdf.ln(4)

    for line in body.split("\n"):
        if not line.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 6, line)
            pdf.ln(1)

    _render_sig_block(pdf)
    pdf.ln(6)

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
                text = await call_giga(token, sp, up, validate=True)
                if _is_refusal(text):
                    print(f"🚫  GigaChat отказал (content filter): пропускаем {filename}")
                    print(f"    Ответ: {text[:200]!r}")
                    continue
                if len(text.strip()) < 300:
                    print(f"⚠  GigaChat вернул слишком короткий текст ({len(text.strip())} симв.): пропускаем {filename}")
                    print(f"    Ответ: {text[:300]!r}")
                    continue

            _raw_before = text
            header_fields = config.get("header_fields", [])
            header = _build_header(header_fields, form_data)
            title = _DOC_TYPE_TITLES.get(config.get("document_type", ""), "ПРЕТЕНЗИЯ")
            body = _parse_body_json(text) if not python_template else text
            body = clean_llm_text(body)
            body = fix_dashes(body)
            if "--debug" in sys.argv:
                print(f"\n--- RAW ({sid}) ---\n{_raw_before[:400]}\n--- AFTER CLEANUP ---\n{body[:400]}\n")
            make_pdf(header, title, body, OUT_DIR / filename)
            print(f"✓  {filename}")
        except Exception as e:
            print(f"\n    ⚠  ошибка ({e!r}), повтор через 3с…", flush=True)
            await asyncio.sleep(3)
            try:
                if python_template:
                    if sid in _HYBRID_ENRICHERS:
                        form_data = _HYBRID_ENRICHERS[sid](form_data)
                    narrative_fields = config.get("narrative_fields", [])
                    narrative_prompt = config.get("narrative_prompt", "")
                    raw_narrative = " ".join(
                        str(form_data.get(f, "")) for f in narrative_fields if form_data.get(f)
                    )
                    if raw_narrative and narrative_prompt:
                        polished = await call_giga(token, narrative_prompt, f"Исправь и перефразируй: {raw_narrative}")
                        polished = raw_narrative if _is_refusal(polished) else polished
                    else:
                        polished = raw_narrative
                    text = pre_substitute_prompt(python_template, form_data)
                    text = text.replace("{{llm_narrative}}", polished)
                else:
                    sp = FORMAT_RULES + "\n" + pre_substitute_prompt(config.get("system_prompt", ""), form_data)
                    up = build_user_prompt(sid, form_data)
                    text = await call_giga(token, sp, up, validate=True)
                header_fields = config.get("header_fields", [])
                header = _build_header(header_fields, form_data)
                title = _DOC_TYPE_TITLES.get(config.get("document_type", ""), "ПРЕТЕНЗИЯ")
                body = _parse_body_json(text) if not python_template else text
                body = clean_llm_text(body)
                body = fix_dashes(body)
                make_pdf(header, title, body, OUT_DIR / filename)
                print(f"✓  {filename}  (retry)")
            except Exception as e2:
                print(f"❌  {sid}: {e2!r}")

    print(f"\nГотово → frontend/public/samples/")


if __name__ == "__main__":
    asyncio.run(main())
