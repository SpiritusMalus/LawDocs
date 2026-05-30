"""
Мониторинг изменений законодательства.

Запускается 1-го числа каждого месяца. Получает перечень новых
федеральных законов с pravo.gov.ru за прошедший месяц, анализирует
их через GigaChat на предмет влияния на шаблоны LawDocs,
отправляет email-отчёт администратору.
"""

import logging
import re
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import settings
from app.services.email import _send

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "lawdocsru@gmail.com"

_TEMPLATE_CATEGORIES = """
- Защита прав потребителей: магазин, маркетплейс, онлайн-курс, туроператор, ремонт, телеком, медицина
- Жилищные отношения: ЖКХ, управляющая компания, аренда жилья, залив квартиры
- Трудовые отношения: зарплата, увольнение, работодатель
- Банки и финансы: кредит, блокировка счёта по 115-ФЗ
- Страхование: ОСАГО, КАСКО, страховые выплаты
- Транспорт: авиаперевозки, ГИБДД, штрафы
- Гражданское судопроизводство: судебный приказ, возражение
"""


async def _fetch_recent_laws(from_date: str, to_date: str) -> list[str]:
    """Забирает заголовки новых ФЗ с pravo.gov.ru за указанный период."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                "https://pravo.gov.ru/proxy/ips/",
                params={
                    "searchserv": "1",
                    "text": "",
                    "DBi": "4",       # Федеральные законы
                    "sortby": "3",    # По дате (новые первые)
                    "count": "40",
                    "pfrom": from_date,
                    "pto": to_date,
                },
                headers={"User-Agent": "LawDocs-Monitor/1.0 (lawdocsru@gmail.com)"},
            )
        if not resp.is_success:
            logger.warning("pravo.gov.ru responded %s", resp.status_code)
            return []

        logger.debug(
            "pravo_gov_raw_html",
            extra={"action": "pravo_gov_raw_html", "length": len(resp.text), "preview": resp.text[:500]},
        )

        # Извлекаем заголовки документов из HTML
        titles = re.findall(
            r'<a[^>]+href="[^"]*"[^>]*>\s*([^<]{25,300}?)\s*</a>',
            resp.text,
        )
        seen: set[str] = set()
        result: list[str] = []
        for t in titles:
            t = t.strip()
            if t and t not in seen and len(t) > 20:
                seen.add(t)
                result.append(t)
            if len(result) >= 30:
                break
        return result
    except Exception as exc:
        logger.warning("pravo.gov.ru fetch failed: %s", exc)
        return []


def _count_relevant(analysis: str) -> int:
    """Считает количество релевантных законов в секции 'Требуют обновления шаблонов'."""
    section_match = re.search(
        r"###\s*Требуют обновления шаблонов\s*\n(.*?)(?=###|\Z)",
        analysis,
        re.DOTALL,
    )
    if not section_match:
        return 0
    section_text = section_match.group(1).strip()
    if not section_text or section_text.lower() in ("нет", "—", "-"):
        return 0
    items = [line for line in section_text.splitlines() if line.strip().startswith(("-", "•", "*", "1"))]
    return len(items) if items else (0 if "нет" in section_text.lower() else 1)


async def _analyze_with_llm(laws: list[str], period: str) -> str:
    from app.services.llm import _call_llm

    laws_block = "\n".join(f"- {law}" for law in laws) if laws else "(список документов недоступен)"

    system_prompt = (
        "Ты — юрисконсульт, специализирующийся на потребительском, жилищном, "
        "трудовом и финансовом праве. Ты отслеживаешь изменения российского "
        "законодательства, которые влияют на юридические документы: претензии, "
        "заявления, жалобы."
    )

    user_prompt = f"""Период мониторинга: {period}

Новые документы за период (из pravo.gov.ru):
{laws_block}

Шаблоны документов LawDocs охватывают:
{_TEMPLATE_CATEGORIES}

Задача:
1. Выдели из перечисленных законы/изменения, которые могут затронуть наши шаблоны.
2. Для каждого релевантного — кратко опиши суть и что именно может потребовать обновления.
3. Если список документов пуст — укажи принятые изменения из своих знаний, которые вступают в силу в ближайшие 3 месяца.

Структура ответа (строго):

### Требуют обновления шаблонов
(по одному пункту на каждый релевантный закон, или «нет» если ничего)

### Вступают в силу в ближайшие 3 месяца
(важные изменения, которые нужно отследить)

### Итог для администратора
(1–3 предложения: что делать сейчас)
"""

    return await _call_llm(system_prompt, user_prompt)


async def _build_link_check_section() -> str:
    """HTML-секция с результатом HTTP-проверки ссылок legal_refs."""
    from app.services.link_check import check_legal_refs

    try:
        results = await check_legal_refs()
    except Exception as exc:
        logger.warning("link_check failed: %s", exc)
        return (
            "<h3 style='color:#374151'>Проверка ссылок на законодательство</h3>"
            "<p style='color:#9ca3af;font-size:13px'>Проверка не выполнена (ошибка).</p>"
        )

    if not results:
        return ""

    total = len(results)
    broken = [r for r in results if not r["ok"]]
    ok_count = total - len(broken)

    if not broken:
        body = (
            f"<p style='color:#16a34a;font-size:14px'>✓ Все ссылки доступны ({total}).</p>"
        )
    else:
        rows = ""
        for r in broken:
            status = r["status"] if r["status"] is not None else r.get("error", "—")
            laws = "; ".join(r["laws"]) or "—"
            situations = ", ".join(r["situations"])
            rows += (
                "<li style='margin-bottom:6px'>"
                f"<span style='color:#dc2626'>[{status}]</span> {laws}<br>"
                f"<span style='color:#64748b;font-size:12px'>ситуации: {situations} · {r['url']}</span>"
                "</li>"
            )
        body = (
            f"<p style='font-size:14px'>Доступно {ok_count} из {total}. "
            f"<strong style='color:#dc2626'>Проблемные ({len(broken)}):</strong></p>"
            f"<ul style='font-size:13px'>{rows}</ul>"
        )

    return f"<h3 style='color:#374151'>Проверка ссылок на законодательство</h3>{body}"


async def run_law_monitor() -> None:
    now = datetime.now(UTC)

    # Период — прошедший месяц
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_last = first_of_this_month - timedelta(days=1)
    last_month_first = last_month_last.replace(day=1)

    from_date = last_month_first.strftime("%d.%m.%Y")
    to_date = last_month_last.strftime("%d.%m.%Y")
    period = f"{from_date} — {to_date}"

    logger.info("law_monitor_start", extra={"action": "law_monitor_start", "period": period})

    laws = await _fetch_recent_laws(from_date, to_date)
    analysis = await _analyze_with_llm(laws, period)
    link_section = await _build_link_check_section()

    relevant_count = _count_relevant(analysis)

    if laws:
        laws_html = "".join(f"<li style='margin-bottom:4px'>{law}</li>" for law in laws)
        laws_section = f"<ul style='font-size:13px'>{laws_html}</ul>"
    else:
        laws_section = "<p style='color:#9ca3af;font-size:13px'>pravo.gov.ru недоступен — используется анализ на основе знаний LLM</p>"

    # Конвертируем markdown ### заголовки в HTML без артефактов
    analysis_html = ""
    for line in analysis.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            analysis_html += f"<strong style='display:block;margin-top:12px'>{stripped[4:]}</strong>"
        elif stripped:
            analysis_html += f"{stripped}<br>"
        else:
            analysis_html += "<br>"

    if relevant_count > 0:
        verdict_color = "#dc2626"
        verdict_text = f"⚠️ Найдено {relevant_count} изменений, требующих обновления шаблонов"
    else:
        verdict_color = "#16a34a"
        verdict_text = "✓ Изменений, требующих обновления шаблонов, не найдено"

    html = f"""
    <div style="font-family:sans-serif;max-width:700px">
      <h2 style="color:#1e293b">Мониторинг законодательства</h2>
      <p style="color:#64748b">{period}</p>

      <div style="background:#f1f5f9;border-left:4px solid {verdict_color};padding:12px 16px;border-radius:4px;margin-bottom:20px">
        <strong style="color:{verdict_color}">{verdict_text}</strong>
      </div>

      <h3 style="color:#374151">Новые документы ({len(laws)} из pravo.gov.ru)</h3>
      {laws_section}

      <h3 style="color:#374151">Анализ LLM</h3>
      <div style="background:#f8fafc;border-left:3px solid #2563eb;padding:16px;border-radius:4px;font-size:14px;line-height:1.7">
        {analysis_html}
      </div>

      {link_section}

      <hr style="margin:24px 0;border:none;border-top:1px solid #e5e7eb">
      <p style="color:#9ca3af;font-size:12px">
        Автоматический отчёт LawDocs · {now.strftime("%d.%m.%Y")}<br>
        Следующий отчёт — 1-го числа следующего месяца.<br>
        Для ручной проверки: сырой HTML pravo.gov.ru доступен в логах (уровень DEBUG, action=pravo_gov_raw_html).
      </p>
    </div>
    """

    await _send(
        to=ADMIN_EMAIL,
        subject=f"LawDocs — мониторинг законодательства за {period}",
        html=html,
    )

    logger.info(
        "law_monitor_done",
        extra={
            "action": "law_monitor_done",
            "period": period,
            "laws_found": len(laws),
            "relevant_count": relevant_count,
        },
    )
