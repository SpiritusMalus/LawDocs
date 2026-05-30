"""
Text cleanup for LLM-generated document body.

Cleans only the body text (no header/title — those are built deterministically).
Used by:
- backend/app/services/llm.py
- scripts/gen_samples.py
"""

import re

_ORG_ABBREVS = frozenset({"ООО", "АО", "ПАО", "ГБУ", "МБУ", "ИП", "ФГУП", "МУП", "ГБУЗ", "ФКУ", "НКО", "КФХ", "ФССП", "ФАС", "РПН"})

_ORG_BOUNDARY = r'(?<![А-ЯЁа-яёA-Za-z])'
_ORG_BOUNDARY_END = r'(?![А-ЯЁа-яёA-Za-z])'

_INLINE_CAPS_RE = re.compile(r'\b([А-ЯЁ]{3,})\b')

_SECTION_LABELS = (
    r'Шапка|Описание|Обоснование(?:\s+по\s+причине)?|Требование|Нарушение|Обстоятельства|Правовое\s+обоснование|'
    r'Расчёт|Предупреждение|Приложени[ея]|Вводная|Реквизиты|Содержательная(?:\s+часть)?|'
    r'Основание\s+несогласия'
)

_SECTION_LABEL_RE = re.compile(r'^(\d+[\.\)]\s*)?[А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s]{2,50}:$')

_SECTION_PREFIX_RE = re.compile(
    r'^(' + _SECTION_LABELS + r')\s*:\s*',
    re.IGNORECASE,
)

_DATE_SIG_RE = re.compile(
    r'^(\d+[\.\)]?\s*)?'
    r'(дата\s+(и\s+)?подпись[:\.]?'
    r'|дата[:\.]?\s*$'
    r'|подпись\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.?){1,2}\.?'
    r'|подпись\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+'
    r'|подпись[:\.]?\s*$'
    r')\s*$',
    re.IGNORECASE,
)

_DOC_DATE_RE = re.compile(
    r'^\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|'
    r'июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*(г\.?|года)?\s*$',
    re.IGNORECASE,
)

_SHORT_DATE_LINE_RE = re.compile(r'^\d{1,2}\.\d{2}\.\d{4}\s*$')

_MARKDOWN_RE = re.compile(r'^#{1,3}\s|^\*{1,3}[^\*]|^-{3,}$')

_TITLE_WORDS = frozenset({"ПРЕТЕНЗИЯ", "ЖАЛОБА", "ВОЗРАЖЕНИЕ", "ЗАЯВЛЕНИЕ", "ХОДАТАЙСТВО", "УВЕДОМЛЕНИЕ"})

_TITLE_WITH_SUBTITLE_RE = re.compile(
    r'^(ПРЕТЕНЗИЯ|ЖАЛОБА|ВОЗРАЖЕНИЕ|ЗАЯВЛЕНИЕ|ХОДАТАЙСТВО|УВЕДОМЛЕНИЕ)\s+\S',
    re.IGNORECASE,
)

_ALL_CAPS_RE = re.compile(r'^[А-ЯЁ\s\d\W]{10,}$')

_TITLE_CASE_MIN_WORDS = 4


def _fix_inline_caps(s: str) -> str:
    """Приводит случайные ALL_CAPS-слова внутри строки к нижнему регистру. Сохраняет аббревиатуры."""
    if s in _TITLE_WORDS:
        return s

    def replacer(m: re.Match) -> str:
        word = m.group(1)
        if word in _ORG_ABBREVS:
            return word
        if len(word) <= 3:
            return word
        return word.lower()

    return _INLINE_CAPS_RE.sub(replacer, s)


def _is_title_case_line(s: str) -> bool:
    """True если строка — Title Case GigaChat-артефакт (≥4 слова, ≥50% с заглавной)."""
    if len(s) <= 20 or s in _TITLE_WORDS:
        return False
    words = re.findall(r'[А-ЯЁа-яё]{3,}', s)
    if len(words) < _TITLE_CASE_MIN_WORDS:
        return False
    return sum(1 for w in words if w[0].isupper()) / len(words) >= 0.5


def _to_sentence_case(s: str) -> str:
    """Title Case → sentence case. Сохраняет аббревиатуры."""
    abbrevs = re.findall(r'\b[А-ЯЁA-Z]{2,5}(?:-\d+)?\b', s)
    result = s[0].upper() + s[1:].lower() if s else s
    result = re.sub(r'(\.\s+)([а-яёa-z])', lambda m: m.group(1) + m.group(2).upper(), result)
    for abbr in abbrevs:
        result = result.replace(abbr.lower(), abbr, 1)
    for org in _ORG_ABBREVS:
        result = re.sub(_ORG_BOUNDARY + org[0] + org[1:].lower() + _ORG_BOUNDARY_END, org, result)
        result = re.sub(_ORG_BOUNDARY + org.lower() + _ORG_BOUNDARY_END, org, result)
    return result


def clean_llm_text(text: str) -> str:
    """Чистит тело документа от LLM-артефактов.

    Не трогает структуру — шапка и заголовок уже отделены.
    Убирает: метки разделов, markdown, даты составления, ALL_CAPS внутри предложений,
    Title Case артефакты, строки с подписью.
    """
    lines = text.split("\n")
    cleaned: list[str] = []

    for line in lines:
        s = line.strip()

        if not s:
            cleaned.append(line)
            continue

        # Пропускаем заголовок документа если LLM всё же его написал
        if s in _TITLE_WORDS or _TITLE_WITH_SUBTITLE_RE.match(s):
            continue

        # "Шапка: Руководителю..." → убираем префикс, оставляем содержание
        m = _SECTION_PREFIX_RE.match(s)
        if m:
            remainder = s[m.end():].strip()
            if not remainder:
                continue
            line = remainder
            s = remainder

        if _DATE_SIG_RE.match(s):
            continue
        if _SECTION_LABEL_RE.match(s):
            continue
        if _DOC_DATE_RE.match(s):
            continue
        if _SHORT_DATE_LINE_RE.match(s):
            continue
        if _MARKDOWN_RE.match(s):
            continue

        # ALL_CAPS строки → word-case
        if _ALL_CAPS_RE.match(s) and len(s) > 15 and s not in _TITLE_WORDS:
            words_result = []
            for word in s.split():
                clean_word = re.sub(r'[«»"\']', '', word)
                if clean_word in _ORG_ABBREVS:
                    words_result.append(word)
                else:
                    words_result.append(word.capitalize())
            cleaned.append(" ".join(words_result))
            continue

        # Title Case → sentence case
        if _is_title_case_line(s):
            cleaned.append(_to_sentence_case(s))
            continue

        # Убираем markdown bold/italic
        line = re.sub(r'\*{2,}([^\*]+)\*{2,}', r'\1', line)
        if not re.search(r'^_+\s*/\s*_+$', s):
            line = re.sub(r'_{2,}([^_]+)_{2,}', r'\1', line)

        # Inline ALL_CAPS слова → строчные (внутри предложений)
        fixed = _fix_inline_caps(line.strip())
        line = line.replace(line.strip(), fixed) if fixed != line.strip() else line

        cleaned.append(line)

    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    # Capitalize первой кириллической буквы строки
    result = re.sub(r'(?m)^([а-яё])', lambda m: m.group(1).upper(), result)
    # Восстанавливаем аббревиатуры
    for org in _ORG_ABBREVS:
        result = re.sub(_ORG_BOUNDARY + org[0] + org[1:].lower() + _ORG_BOUNDARY_END, org, result)
        result = re.sub(_ORG_BOUNDARY + org.lower() + _ORG_BOUNDARY_END, org, result)
    return result


def fix_dashes(text: str) -> str:
    """Заменяет двойные/тройные дефисы и en-dash на длинное тире (—), схлопывает
    соседние длинные тире (— —), возникающие при пустых полях-разделителях."""
    text = re.sub(r'-{2,}', '—', text)
    text = re.sub(r'–{2,}', '—', text)
    text = re.sub(r'[-–][-–]+', '—', text)
    text = re.sub(r'(?m)^- ', '— ', text)
    # Соседние длинные тире (с пробелами между) → одно
    text = re.sub(r'—(?:\s*—)+', '—', text)
    return text


_QUALITY_ARTIFACTS = (
    re.compile(
        r'^(' + _SECTION_LABELS + r')\s*:',
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r'^Если\s+\w[\w_]*\s*[=:]', re.IGNORECASE | re.MULTILINE),
    re.compile(r'\*{2,}[^\*]+\*{2,}'),
    re.compile(r'\b(violation_type|has_photo|problem_type|damage_claim|night_calls|fine_number|gibdd_unit)\b'),
    re.compile(r'-{2,}'),
    # Незаполненные шаблонные плейсхолдеры
    re.compile(r'\{\{[^}]+\}\}'),
    re.compile(r'\[calculated_[^\]]*\]'),
    # Отказ GigaChat отвечать
    re.compile(
        r'\b(не могу|не в состоянии|как (языковая|ИИ)|как искусственный интеллект|'
        r'извините, но я|отказываюсь|это невозможно|за пределами моих возможностей)\b',
        re.IGNORECASE,
    ),
)

_MIN_QUALITY_LENGTH = 200


def has_quality_artifacts(text: str) -> bool:
    """True если текст содержит артефакты качества или слишком короткий (повод для retry)."""
    if len(text.strip()) < _MIN_QUALITY_LENGTH:
        return True
    return any(pattern.search(text) for pattern in _QUALITY_ARTIFACTS)
