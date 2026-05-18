"""
LLM-сервис: GigaChat.

GigaChat API совместим с OpenAI-форматом (chat completions).
Авторизация: OAuth2 через RqUID + Base64(client_id:client_secret).
"""

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime

import httpx

from app.core.config import settings

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


async def _call_gigachat(system_prompt: str, user_prompt: str) -> str:
    token = await _get_gigachat_token()
    async with httpx.AsyncClient(verify=_get_verify()) as client:
        resp = await client.post(
            f"{GIGACHAT_API_URL}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


_MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря"]

_FORMAT_RULES = """ПРАВИЛА ФОРМАТИРОВАНИЯ — строго обязательны:

1. Выводи ТОЛЬКО готовый текст документа. Никаких пояснений, предисловий, комментариев, вступлений от себя.

1а. НЕ пиши нигде в документе дату его составления в любом формате («сегодня», «18 мая 2026 года», «29.04.2026», «на дату подачи», «на текущую дату» и т.д.) — дату заявитель впишет от руки при подписании. Используй только даты событий из данных формы (дата покупки, дата нарушения и т.п.). Пункт «Дата и подпись» в инструкции означает, что это место для бланка — НЕ выводи ни дату, ни подпись, ни метку «Дата и подпись».

2. НЕ выводи метки разделов в тексте: «Шапка:», «Заголовок:», «Описание:», «Нарушение:», «Обстоятельства:», «Правовое обоснование:», «Требование:», «Дата и подпись», «Подпись:», «Расчёт компенсации:», «Расчёт:» и любые подобные. Пиши сразу содержание без метки.

3. НЕ используй markdown: никаких **жирный**, *курсив*, # заголовки, --- линии.

4. НЕ пиши текст ЗАГЛАВНЫМИ буквами нигде в документе, включая ФИО, расчёты, итоги, требования и любые другие части. Единственное исключение — само название документа (ПРЕТЕНЗИЯ / ЖАЛОБА / ВОЗРАЖЕНИЕ / ЗАЯВЛЕНИЕ), оно пишется отдельной строкой заглавными без кавычек. Запрещено: «ИТОГО К ВЫПЛАТЕ», «ПРОШУ ВАС ВЫПЛАТИТЬ», «ТРЕБУЮ», «В СВЯЗИ С ВЫШЕИЗЛОЖЕННЫМ» и любые подобные — всё обычным регистром с заглавной буквы.

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
    lines = [f"Ситуация: {situation_id}", "", "Данные пользователя:"]
    for k, v in form_data.items():
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


def _pre_substitute_prompt(system_prompt: str, form_data: dict) -> str:
    """Подставляет реальные значения вместо [field_name] в system_prompt."""
    def replacer(m: re.Match) -> str:
        key = m.group(1)
        if key in form_data and form_data[key]:
            return _sanitize_value(str(form_data[key]))
        for alias_key, candidates in _FIELD_ALIASES.items():
            if key == alias_key:
                for candidate in candidates:
                    if candidate in form_data and form_data[candidate]:
                        return _sanitize_value(str(form_data[candidate]))
        return m.group(0)
    return re.sub(r"\[([a-z_]+)\]", replacer, system_prompt)


async def fill_instruction(situation_id: str, form_data: dict) -> str:
    if not settings.GIGACHAT_AUTH_KEY:
        raise RuntimeError("GigaChat not configured — set GIGACHAT_AUTH_KEY")

    situation_type = _SITUATION_TYPES.get(situation_id, situation_id)
    company = _get_company_name(situation_id, form_data)
    company_line = f"Компания: {company}" if company else "Компания: не указана"

    user_prompt = f"Тип ситуации: {situation_type}\n{company_line}"
    return await _call_gigachat(_INSTRUCTION_SYSTEM_PROMPT, user_prompt)


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
        polished = await _call_gigachat(
            config.narrative_prompt,
            f"Исправь и перефразируй: {raw_narrative}",
        )
        if _is_gigachat_refusal(polished):
            logger.warning(
                "GigaChat refused to polish narrative for hybrid template, using raw text"
            )
            polished = raw_narrative
    else:
        polished = raw_narrative

    text = _pre_substitute_prompt(config.python_template, form_data)
    text = text.replace("{{llm_narrative}}", polished)
    return text


async def fill_template(situation_id: str, form_data: dict) -> str:
    from app.situations.registry import registry

    if not settings.GIGACHAT_AUTH_KEY:
        raise RuntimeError("GigaChat not configured — set GIGACHAT_AUTH_KEY")

    config = registry.get(situation_id)

    if config and config.python_template:
        return await _fill_template_hybrid(config, form_data)

    base_prompt = config.system_prompt if config else _DEFAULT_SYSTEM_PROMPT
    system_prompt = _FORMAT_RULES + "\n" + _pre_substitute_prompt(base_prompt, form_data)
    user_prompt = _build_user_prompt(situation_id, form_data)

    text = await _call_gigachat(system_prompt, user_prompt)
    if _is_gigachat_refusal(text):
        logger.error(
            "GigaChat refused to generate document for situation=%s: %r",
            situation_id, text[:200],
        )
        raise RuntimeError(
            f"GigaChat отказал в генерации документа для ситуации '{situation_id}'. "
            "Ответ содержит отказ вместо документа."
        )
    return text
