"""
LLM-сервис: GigaChat.

GigaChat API совместим с OpenAI-форматом (chat completions).
Авторизация: OAuth2 через RqUID + Base64(client_id:client_secret).
"""

import asyncio
import logging
import re
import uuid
from datetime import UTC, date, datetime

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.pii_classifier import split_for_llm
from app.services.text_cleanup import clean_llm_text, fix_dashes, has_quality_artifacts

logger = logging.getLogger(__name__)

_MAX_FIELD_VALUE_LEN = 1000


def _get_verify() -> str | bool:
    """Возвращает параметр verify для httpx.

    Если задан GIGACHAT_CA_CERT — использует его как путь к CA-bundle.
    В продакшне без CA — RuntimeError: тихое отключение TLS недопустимо.
    """
    if settings.GIGACHAT_CA_CERT:
        return settings.GIGACHAT_CA_CERT
    if settings.APP_ENV == "production":
        raise RuntimeError(
            "GIGACHAT_CA_CERT не задан в production. "
            "Скачайте CA Минцифры и укажите путь к .pem в .env."
        )
    return False


def _sanitize_value(value: str) -> str:
    """Обрезает значение и нормализует whitespace перед вставкой в LLM-промпт."""
    value = value[:_MAX_FIELD_VALUE_LEN]
    # Заменяем переносы строк пробелом — иначе пользователь может сломать
    # структуру промпта и вставить ложные поля.
    return " ".join(value.split())


_gigachat_token: str | None = None
_gigachat_token_expires_at: datetime | None = None
_gigachat_lock = asyncio.Lock()

GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"


async def _get_gigachat_token() -> str:
    global _gigachat_token, _gigachat_token_expires_at

    async with _gigachat_lock:
        if (
            _gigachat_token
            and _gigachat_token_expires_at
            and _gigachat_token_expires_at > datetime.now(UTC)
        ):
            return _gigachat_token

        # verify=False: GigaChat использует CA «МинЦифры России», не входящий
        # в стандартный доверенный список. В продакшне можно добавить CA-cert
        # через httpx.AsyncClient(verify="/path/to/mintsifry_ca.pem").
        async with httpx.AsyncClient(verify=_get_verify()) as client:
            resp = await client.post(
                GIGACHAT_AUTH_URL,
                headers={
                    "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=10,
            )
            if not resp.is_success:
                logger.error("GigaChat auth failed %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
            data = resp.json()

        _gigachat_token = data["access_token"]
        _gigachat_token_expires_at = datetime.fromtimestamp(data["expires_at"] / 1000, tz=UTC)
        return _gigachat_token


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


async def _call_gigachat(system_prompt: str, user_prompt: str, *, validate: bool = False) -> str:
    """Вызывает GigaChat. При validate=True делает до 2 retry при артефактах в ответе."""

    async def _once(extra_feedback: str = "") -> str:
        # Токен перезапрашивается каждый раз — защита от истечения между retry
        fresh_token = await _get_gigachat_token()
        for net_attempt in range(1, 3):
            try:
                async with httpx.AsyncClient(verify=_get_verify()) as client:
                    resp = await client.post(
                        f"{GIGACHAT_API_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {fresh_token}"},
                        json={
                            "model": "GigaChat",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt + extra_feedback},
                            ],
                            "temperature": 0.2,
                            "max_tokens": 4096,
                        },
                        timeout=60,
                    )
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if net_attempt == 2:
                    raise
                logger.warning("GigaChat network error (attempt %d): %s, retrying", net_attempt, e)
                await asyncio.sleep(2)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (500, 502, 503) and net_attempt < 2:
                    logger.warning("GigaChat %d (attempt %d), retrying", e.response.status_code, net_attempt)
                    await asyncio.sleep(2)
                    continue
                raise
        raise RuntimeError("unreachable")

    text = await _once()

    if validate:
        for attempt in range(1, 3):
            if not has_quality_artifacts(text):
                break
            logger.warning(
                "GigaChat response has quality artifacts (attempt %d), retrying", attempt
            )
            text = await _once(_RETRY_FEEDBACK)

    return text


_MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря"]

_FORMAT_RULES = """ПРАВИЛА ФОРМАТИРОВАНИЯ — строго обязательны:

1. Верни ТОЛЬКО JSON строго в таком формате, без пояснений, предисловий и комментариев:
   {"body": "текст тела документа"}
   Шапку (кому/от кого) и заголовок (ПРЕТЕНЗИЯ / ЖАЛОБА) НЕ пиши — они формируются автоматически.
   Начинай тело с первого абзаца по существу.

2. НЕ пиши нигде в теле дату составления документа в любом формате — дату заявитель впишет от руки. Используй только даты событий из данных формы (дата покупки, дата нарушения и т.п.).

3. НЕ выводи метки разделов: «Описание:», «Нарушение:», «Обстоятельства:», «Правовое обоснование:», «Требование:», «Расчёт:» и подобные. Пиши сразу содержание.

4. НЕ используй markdown: никаких **жирный**, *курсив*, # заголовки, --- линии.

5. НЕ пиши текст ЗАГЛАВНЫМИ буквами нигде в теле. Всё обычным регистром с заглавной буквы.

6. НЕ упоминай имена переменных и кодовые значения из формы (violation_type, problem_type и т.д.) — применяй их смысл по-русски.

7. НЕ пиши условную логику («если X = Y»). Просто применяй её молча.

8. Используй ТОЛЬКО длинное тире (—). Одинарный дефис (-) в роли паузы — ЗАПРЕЩЁН.

9. Аббревиатуры ООО, АО, ПАО, ГБУ, МБУ, ИП, ФГУП, МУП — ВСЕГДА заглавными буквами.

10. Дату и подпись не выводи — они добавляются автоматически.
"""

_REVIEW_SYSTEM_PROMPT = """Ты — корректор юридических документов. Тебе дано готовое тело претензии/жалобы/заявления. Документ уже составлен — твоя задача ТОЛЬКО вычитать и убрать дефекты форматирования. Это финальная вычитка, а не переписывание.

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- Перефразировать, переписывать или сокращать предложения
- Менять формулировки, факты, цифры, суммы, даты, названия, ссылки на статьи законов
- Менять структуру, порядок абзацев, удалять или добавлять содержание
- «Улучшать» стиль

УБЕРИ ТОЛЬКО эти дефекты, не трогая остальной текст дословно:
1. Метки разделов в начале абзаца: «Описание:», «Требование:», «Правовое обоснование:» — удали саму метку, текст после неё оставь
2. Markdown-разметку: **жирный**, *курсив*, # заголовки, --- линии — убери символы, текст сохрани
3. ЗАГЛАВНЫЕ слова внутри предложений → обычный регистр: «БАНКом» → «банком» (аббревиатуры ООО, АО, ПАО, ГБУ, МБУ, ИП, ФГУП, МУП — оставь ЗАГЛАВНЫМИ)
4. Двойное тире (--) и одинарный дефис в роли паузы → длинное тире (—)

Если дефектов нет — верни текст ПОЛНОСТЬЮ без изменений, дословно.
ВЕРНИ: только текст тела целиком, без пояснений, без обрезки."""

async def _call_yandex_review(draft: str) -> tuple[str, bool]:
    """Мягкая вычитка YandexGPT: убирает дефекты форматирования, НЕ переписывая текст.

    Подстраховщик, а не второй автор. Возвращает (текст, yandex_ok). При любом
    подозрении на порчу (обрезка по токенам, заметное укорачивание = выброшенное
    содержание) возвращает исходный черновик GigaChat — yandex_ok=False, и вызывающий
    оставляет версию GigaChat как есть.
    """
    if not settings.YANDEX_API_KEY or not settings.YANDEX_FOLDER_ID:
        logger.warning("YandexGPT not configured, skipping review pass")
        return draft, False

    client = AsyncOpenAI(
        api_key=settings.YANDEX_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
    )

    for attempt in range(1, 3):
        try:
            response = await client.chat.completions.create(
                model=f"gpt://{settings.YANDEX_FOLDER_ID}/yandexgpt-5-pro/latest",
                messages=[
                    {"role": "system", "content": _REVIEW_SYSTEM_PROMPT},
                    {"role": "user", "content": draft},
                ],
                temperature=0,
                max_tokens=8192,
                extra_body={"folder_id": settings.YANDEX_FOLDER_ID},
                timeout=90,
            )
            choice = response.choices[0]
            result = choice.message.content
            if not result or not result.strip():
                logger.error("YandexGPT returned empty response (attempt %d)", attempt)
                return draft, False
            # Обрезка по лимиту токенов → вычитка неполная, документ сломан. Отбрасываем.
            if getattr(choice, "finish_reason", None) == "length":
                logger.warning("YandexGPT review truncated (finish_reason=length), keeping GigaChat draft")
                return draft, False
            # Защита от выброшенного содержания: вычитка не должна заметно укорачивать текст.
            if len(result.strip()) < 0.85 * len(draft.strip()):
                logger.warning(
                    "YandexGPT review shrank text %d→%d chars, keeping GigaChat draft",
                    len(draft.strip()), len(result.strip()),
                )
                return draft, False
            return result, True
        except Exception as e:
            logger.error("YandexGPT review failed attempt %d (%s: %s)", attempt, type(e).__name__, str(e))
            if attempt == 2:
                from app.services.notifications import send_telegram_alert
                await send_telegram_alert(f"⚠️ YandexGPT review failed: {type(e).__name__}: {str(e)[:100]}")
                return draft, False
            await asyncio.sleep(2)

    return draft, False


async def _call_yandex_primary(system_prompt: str, user_prompt: str) -> str:
    """YandexGPT Pro как первичный генератор — fallback при отказе GigaChat."""
    if not settings.YANDEX_API_KEY or not settings.YANDEX_FOLDER_ID:
        raise RuntimeError("YandexGPT not configured — set YANDEX_API_KEY and YANDEX_FOLDER_ID")

    client = AsyncOpenAI(
        api_key=settings.YANDEX_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
    )

    for attempt in range(1, 3):
        try:
            response = await client.chat.completions.create(
                model=f"gpt://{settings.YANDEX_FOLDER_ID}/yandexgpt-5-pro/latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
                extra_body={"folder_id": settings.YANDEX_FOLDER_ID},
                timeout=60,
            )
            result = response.choices[0].message.content
            if not result or not result.strip():
                raise RuntimeError("YandexGPT returned empty response")
            return result
        except Exception as e:
            logger.error("YandexGPT primary attempt %d: %s: %s", attempt, type(e).__name__, str(e))
            if attempt == 2:
                raise RuntimeError(f"YandexGPT primary failed: {e}") from e
            await asyncio.sleep(2)

    raise RuntimeError("unreachable")


async def _call_llm(system_prompt: str, user_prompt: str, *, validate: bool = False) -> str:
    """Диспетчер LLM: GigaChat первый, YandexGPT Pro при отказе или отсутствии GigaChat."""
    if not settings.GIGACHAT_AUTH_KEY:
        logger.info("GigaChat not configured, using YandexGPT as primary")
        return await _call_yandex_primary(system_prompt, user_prompt)

    text = await _call_gigachat(system_prompt, user_prompt, validate=validate)

    if _is_gigachat_refusal(text):
        logger.warning("GigaChat refused, falling back to YandexGPT primary")
        if not settings.YANDEX_API_KEY or not settings.YANDEX_FOLDER_ID:
            raise RuntimeError(
                "GigaChat refused and YandexGPT not configured — "
                "set YANDEX_API_KEY + YANDEX_FOLDER_ID to enable fallback."
            )
        return await _call_yandex_primary(system_prompt, user_prompt)

    return text


_REFUSAL_MARKERS = (
    "временно ограничены",
    "генеративные языковые модели",
    "языковая модель",
    "не могу помочь",
    "не могу выполнить",
    "не могу составить",
    "не предоставляю",
    "обратитесь к специалисту",
    "чувствительные темы",
    "не обладают собственным мнением",
    "ограничены разговоры",
)


def _is_gigachat_refusal(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _REFUSAL_MARKERS)


# ── Постобработка и валидация ответа GigaChat ─────────────────────────────────
# (all patterns and logic moved to app.services.text_cleanup)


def _has_quality_artifacts(text: str) -> bool:
    """Проверяет, содержит ли текст типичные артефакты GigaChat."""
    if not has_quality_artifacts(text):
        return False
    # Слишком короткий — не документ
    if len(text.strip()) < 300:
        return True
    return False


_DEFAULT_SYSTEM_PROMPT = """Ты — опытный юрист. Составь официальную претензию или жалобу.
Используй официально-деловой стиль. Ссылайся только на реальные нормы российского права.

Правила:
- Официально-деловой стиль, без эмоций и просторечий
- Ссылайся на конкретные статьи закона (не выдумывай несуществующие)
- Не придумывай факты — используй только данные пользователя
- Квадратные скобки [...] используй ТОЛЬКО для данных, которых нет в форме
- Все данные из формы вставляй напрямую — БЕЗ квадратных скобок
- Верни ТОЛЬКО текст документа, без пояснений и комментариев"""


def _build_user_prompt(situation_id: str, form_data: dict) -> str:
    """Промпт с данными пользователя для GigaChat.

    В LLM уходят ТОЛЬКО безопасные поля (TEXT/ROUTING). ПДн (имена, адреса, суммы,
    идентификаторы) сюда НЕ попадают — они подставляются в готовый документ локально
    через _post_substitute_output. Граница приватности — app.services.pii_classifier.
    """
    safe, _sensitive = split_for_llm(form_data)
    today = date.today().strftime("%d.%m.%Y")
    lines = [f"Ситуация: {situation_id}", f"Текущая дата: {today}", "", "Данные пользователя:"]
    for k, v in safe.items():
        if v:
            lines.append(f"- {k}: {_sanitize_value(str(v))}")
    return "\n".join(lines)


_INSTRUCTION_SYSTEM_PROMPT = """Ты — помощник юриста. Составь краткую практическую инструкцию для человека, который уже написал претензию и хочет её подать.

Инструкция должна содержать 4 раздела:
1. Контакты компании (телефон для жалоб, email для претензий, почтовый адрес для заказных писем)
2. Как подать претензию (2–3 конкретных варианта: лично, заказным письмом, через сайт)
3. Сроки (через сколько дней ждать ответа по закону)
4. Куда обратиться если откажут (конкретный контролирующий орган + суд)

Для раздела "Контакты компании":
- Если знаешь реальные контакты конкретной компании из данных пользователя — укажи их точно
- Если НЕ знаешь точных контактов — напиши: "Контакты не найдены автоматически. Найдите самостоятельно: [что именно — телефон горячей линии / email для претензий / юридический адрес] на официальном сайте компании в разделе [куда смотреть: «Контакты» / «Обратная связь» / «О компании» / «Правовые документы»]"

Стиль: простой и понятный, без юридического жаргона. Не более 350 слов.
Верни ТОЛЬКО текст инструкции, без вступлений, заголовков и пояснений."""

_SITUATION_TYPES = {
    "shop": "розничный магазин",
    "marketplace": "маркетплейс (интернет-торговля)",
    "bank": "банк",
    "bank_block": "банк (блокировка счёта по 115-ФЗ)",
    "employer": "работодатель",
    "insurance": "страховая компания",
    "utility": "управляющая компания / ТСЖ",
    "airline": "авиакомпания",
    "court_order": "суд (отмена судебного приказа)",
    "gibdd": "ГИБДД (оспаривание штрафа)",
    "rental_deposit": "арендодатель (удержание залога)",
    "tour_operator": "туроператор (невозврат денег за тур)",
    "online_course": "онлайн-школа (невозврат денег за курс)",
    "neighbor_flood": "сосед (затопление квартиры)",
    "repair": "подрядчик (некачественный ремонт)",
    "telecom": "телекоммуникационная компания (интернет / телефон)",
    "medical": "медицинская организация (нарушение прав пациента)",
    "ddu_delay": "застройщик (долевое строительство, просрочка передачи)",
    "ddu_defects": "застройщик (долевое строительство, строительные недостатки)",
    "ddu_termination": "застройщик (долевое строительство, расторжение ДДУ)",
    "dtp_osago": "страховая компания (ОСАГО, просрочка или занижение выплаты)",
    "auto_repair": "автосервис (некачественный ремонт или задержка)",
    "debt_collector": "коллекторская организация (нарушение ФЗ-230)",
    "carsharing": "каршеринговая компания (необоснованный ущерб)",
    "gym_refund": "фитнес-клуб (возврат за неиспользованный абонемент)",
}


def _get_company_name(situation_id: str, form_data: dict) -> str:
    for key in ("store_name", "airline", "bank_name", "insurance_company", "company_name", "platform"):
        if val := form_data.get(key):
            return str(val)
    return ""


_FIELD_ALIASES: dict[str, list[str]] = {
    "full_name":       ["user_full_name", "full_name"],
    "contact_address": ["user_address", "contact_address"],
    "phone":           ["user_phone", "phone"],
    "email":           ["user_email", "email"],
    "name":            ["user_full_name", "full_name", "name"],
    "address":         ["user_address", "contact_address", "address"],
}


def _substitute_field_placeholders(text: str, form_data: dict) -> str:
    """Подставляет реальные значения вместо [field_name] в тексте.

    Используется в двух местах:
    - локально в python_template гибридного режима (текст в LLM не уходит);
    - в ВЫХОДЕ GigaChat (полный режим) — так ПДн подставляются после генерации,
      а сам промпт их не содержит.
    """
    def replacer(m: re.Match) -> str:
        key = m.group(1)
        if key in form_data:
            value = form_data[key]
            if value:
                return _sanitize_value(str(value))
            return ""
        for alias_key, candidates in _FIELD_ALIASES.items():
            if key == alias_key:
                for candidate in candidates:
                    if candidate in form_data and form_data[candidate]:
                        return _sanitize_value(str(form_data[candidate]))
        return m.group(0)
    return re.sub(r"\[([a-z_]+)\]", replacer, text)


def _pre_substitute_prompt(system_prompt: str, form_data: dict) -> str:
    """Локальная подстановка [field] в шаблон (гибридный режим, не уходит в LLM)."""
    return _substitute_field_placeholders(system_prompt, form_data)


def _post_substitute_output(text: str, form_data: dict) -> str:
    """Подставляет ПДн в ГОТОВЫЙ текст документа от GigaChat (полный режим)."""
    text = _substitute_field_placeholders(text, form_data)
    text = fix_dashes(text)
    return text


async def fill_instruction(situation_id: str, form_data: dict) -> str:
    if not settings.GIGACHAT_AUTH_KEY and (not settings.YANDEX_API_KEY or not settings.YANDEX_FOLDER_ID):
        raise RuntimeError("No LLM configured — set GIGACHAT_AUTH_KEY or (YANDEX_API_KEY + YANDEX_FOLDER_ID)")

    situation_type = _SITUATION_TYPES.get(situation_id, situation_id)
    company = _get_company_name(situation_id, form_data)
    company_line = f"Компания: {company}" if company else "Компания: не указана"

    user_prompt = f"Тип ситуации: {situation_type}\n{company_line}"
    return await _call_llm(_INSTRUCTION_SYSTEM_PROMPT, user_prompt)


async def _fill_template_hybrid(config, form_data: dict) -> str:
    """Гибридный режим: Python рендерит структуру, LLM перефразирует только нарратив клиента.

    Используется для ситуаций, где content filter GigaChat блокирует полную генерацию.
    Структура документа (шапка, правовые нормы, расчёты, требования) — фиксированная.
    LLM получает только текст клиента и возвращает его официально-деловым стилем.
    """
    raw_narrative = " ".join(
        str(form_data.get(f, "")) for f in config.narrative_fields if form_data.get(f)
    )

    if raw_narrative and config.narrative_prompt:
        polished = await _call_llm(
            config.narrative_prompt,
            f"Исправь и перефразируй: {raw_narrative}",
        )
        # Подстраховщик: YandexGPT мягко вычитывает ТОЛЬКО нарратив (творчество LLM).
        # Python-секции (законы, расчёты, требования) детерминированы — их не трогаем.
        # При обрезке/искажении остаётся версия GigaChat (см. _call_yandex_review).
        reviewed, yandex_ok = await _call_yandex_review(polished)
        if yandex_ok:
            polished = reviewed
    else:
        polished = raw_narrative

    text = _pre_substitute_prompt(config.python_template, form_data)
    text = text.replace("{{llm_narrative}}", polished)
    # Лёгкая подчистка детерминированного текста (полный clean_llm_text НЕ применяем,
    # чтобы не перетряхивать структуру шаблона):
    text = fix_dashes(text)
    text = re.sub(r'(?<!\.)\.\.(?!\.)', '.', text)          # двойная точка «руб..» → «.»
    # Заглавная буква после точки (фрагменты склеены как «… ДТП. виновник …»)
    text = re.sub(r'(?<=[.!?]\s)([а-яё])', lambda m: m.group(1).upper(), text)
    # Схлопываем пустые строки от пустого {{llm_narrative}} (нет нарратива)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


def _parse_body_json(raw: str) -> str:
    """Извлекает поле body из JSON-ответа GigaChat.

    GigaChat иногда оборачивает JSON в ```json ... ```. Пробуем несколько стратегий.
    """
    import json

    text = raw.strip()
    # Убираем возможный markdown-блок
    if text.startswith("```"):
        text = re.sub(r'^```[a-z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text.rstrip())
        text = text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict) and "body" in data:
            return str(data["body"]).strip()
    except json.JSONDecodeError:
        pass

    # Fallback: ищем "body": "..." или "body": """..."""
    m = re.search(r'"body"\s*:\s*"(.*?)"', text, re.DOTALL)
    if m:
        return m.group(1).replace('\\n', '\n').strip()

    # Если JSON не распознан — поднимаем ошибку, чтобы не вставить сырой отказ в документ
    logger.error("Could not parse JSON body from GigaChat response: %s", text[:200])
    raise RuntimeError("GigaChat вернул ответ в неожиданном формате (не удалось извлечь body).")


async def fill_template(situation_id: str, form_data: dict) -> tuple[str, list[str], str]:
    """Генерирует тело документа через LLM. Возвращает (body, header, title).

    body  — текст тела (только содержательная часть, без шапки и заголовка).
    header — строки шапки, построенные детерминированно из form_data.
    title  — заголовок документа (ПРЕТЕНЗИЯ / ЖАЛОБА / ...).
    """
    from app.services.docgen import _build_header
    from app.situations.registry import registry

    if not settings.GIGACHAT_AUTH_KEY and (not settings.YANDEX_API_KEY or not settings.YANDEX_FOLDER_ID):
        raise RuntimeError("No LLM configured — set GIGACHAT_AUTH_KEY or (YANDEX_API_KEY + YANDEX_FOLDER_ID)")

    config = registry.get(situation_id)

    # Строим шапку детерминированно — LLM её не видит
    header = _build_header(config.header_fields if config else [], form_data)

    # Заголовок из конфига
    _DOC_TYPE_TITLES = {
        "pretenziya": "ПРЕТЕНЗИЯ",
        "zhaloba": "ЖАЛОБА",
        "zayavlenie": "ЗАЯВЛЕНИЕ",
        "vozrazhenie": "ВОЗРАЖЕНИЕ",
        "hodatajstvo": "ХОДАТАЙСТВО",
        "uvedomlenie": "УВЕДОМЛЕНИЕ",
    }
    title = _DOC_TYPE_TITLES.get(config.document_type if config else "", "ПРЕТЕНЗИЯ")

    if config and config.python_template:
        body = await _fill_template_hybrid(config, form_data)
        return body, header, title

    base_prompt = config.system_prompt if config else _DEFAULT_SYSTEM_PROMPT
    system_prompt = _FORMAT_RULES + "\n" + base_prompt
    user_prompt = _build_user_prompt(situation_id, form_data)

    raw = await _call_llm(system_prompt, user_prompt, validate=True)

    body = _parse_body_json(raw)
    body = clean_llm_text(body)
    if len(body.strip()) < 20:
        raise RuntimeError("LLM body too short after cleanup — possible empty or artifact-only response.")

    # YandexGPT — подстраховщик: мягкая вычитка форматирования. Если он отработал
    # безопасно — берём его версию; если недоступен/обрезал/исказил — оставляем
    # готовый текст GigaChat КАК ЕСТЬ (он уже корректен, прогнан через clean_llm_text).
    reviewed_body, yandex_ok = await _call_yandex_review(body)
    if yandex_ok:
        body = clean_llm_text(reviewed_body)
    else:
        logger.info("YandexGPT review unavailable/rejected, keeping GigaChat draft")

    body = _post_substitute_output(body, form_data)
    return body, header, title
