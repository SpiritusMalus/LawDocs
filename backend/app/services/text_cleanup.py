"""
Unified text cleanup for LLM outputs.

Used by:
- backend/app/services/llm.py (API document generation)
- scripts/gen_samples.py (sample PDF generation)

Single source of truth for all text postprocessing rules.
"""

import re
from datetime import date

_TITLE_WORDS = frozenset({"ПРЕТЕНЗИЯ", "ЖАЛОБА", "ВОЗРАЖЕНИЕ", "ЗАЯВЛЕНИЕ", "ХОДАТАЙСТВО", "УВЕДОМЛЕНИЕ"})

_SECTION_LABELS = (
    r'Шапка|Описание|Обоснование(?:\s+по\s+причине)?|Требование|Нарушение|Обстоятельства|Правовое\s+обоснование|'
    r'Расчёт|Предупреждение|Приложени[ея]|Вводная|Реквизиты|Содержательная(?:\s+часть)?|'
    r'Основание\s+несогласия'
)

_TITLE_WITH_SUBTITLE_RE = re.compile(
    r'^(ПРЕТЕНЗИЯ|ЖАЛОБА|ВОЗРАЖЕНИЕ|ЗАЯВЛЕНИЕ|ХОДАТАЙСТВО|УВЕДОМЛЕНИЕ)\s+\S',
    re.IGNORECASE,
)

_SECTION_LABEL_RE = re.compile(r'^(\d+[\.\)]\s*)?[А-ЯЁа-яёA-Za-z][А-ЯЁа-яёA-Za-z\s]{2,50}:$')

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

_CITY_LINE_RE = re.compile(r'^г\.\s+[А-ЯЁ][а-яё]+(,\s*\d{1,2}\s+\w+\s+\d{4}.*)?\.?\s*$')

_DOC_DATE_RE = re.compile(
    r'^\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|'
    r'июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*(г\.?|года)?\s*$',
    re.IGNORECASE,
)

_SHORT_DATE_LINE_RE = re.compile(r'^\d{1,2}\.\d{2}\.\d{4}\s*$')

_MARKDOWN_RE = re.compile(r'^#{1,3}\s|^\*{1,3}[^\*]|^-{3,}$')

_ALL_CAPS_RE = re.compile(r'^[А-ЯЁ\s\d\W]{10,}$')

_TITLE_CASE_MIN_WORDS = 4

_HEADER_MARKER_RE = re.compile(
    r'^(Мировому\s|В\s+районный|В\s+суд|Начальнику|Руководителю|'
    r'От\s*:|Взыскатель\s*:|Должник\s*:|Дело\s*№)',
    re.IGNORECASE,
)


def reorder_header_before_title(text: str) -> str:
    """Если заголовок документа стоит перед шапкой — переставляет шапку наверх."""
    lines = text.split('\n')
    title_idx = next((i for i, l in enumerate(lines) if l.strip() in _TITLE_WORDS), None)
    if title_idx is None:
        return text
    non_empty_before = [l for l in lines[:title_idx] if l.strip()]
    if non_empty_before:
        return text  # порядок уже верный
    # Ищем шапку после заголовка
    after = lines[title_idx + 1:]
    header_lines, rest_lines, in_header = [], [], True
    for line in after:
        if in_header and line.strip() and _HEADER_MARKER_RE.match(line.strip()):
            header_lines.append(line)
        else:
            in_header = False
            rest_lines.append(line)
    if not header_lines:
        return text
    return '\n'.join(lines[:title_idx] + header_lines + [''] + [lines[title_idx]] + rest_lines)


_ORG_ABBREVS = frozenset({"ООО", "АО", "ПАО", "ГБУ", "МБУ", "ИП", "ФГУП", "МУП", "ГБУЗ", "ФКУ", "НКО", "КФХ", "ФССП", "ФАС", "РПН"})

_INLINE_CAPS_RE = re.compile(r'\b([А-ЯЁ]{3,})\b')

# \b не работает для кириллицы в Python — используем lookaround
_ORG_BOUNDARY = r'(?<![А-ЯЁа-яёA-Za-z])'
_ORG_BOUNDARY_END = r'(?![А-ЯЁа-яёA-Za-z])'


def _fix_inline_caps(s: str) -> str:
    """Приводит случайные ALL_CAPS-слова внутри строки к нижнему регистру.

    Сохраняет аббревиатуры из regexps и _ORG_ABBREVS.
    Не трогает строки, которые сами по себе являются заголовком документа.
    """
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
    """Title Case → sentence case. Сохраняет аббревиатуры (ФЗ, ГК, ООО, ИП)."""
    abbrevs = re.findall(r'\b[А-ЯЁA-Z]{2,5}(?:-\d+)?\b', s)
    result = s[0].upper() + s[1:].lower() if s else s
    # capitalize после ". "
    result = re.sub(r'(\.\s+)([а-яёa-z])', lambda m: m.group(1) + m.group(2).upper(), result)
    for abbr in abbrevs:
        result = result.replace(abbr.lower(), abbr, 1)
    # Восстанавливаем аббревиатуры организационно-правовых форм которые могли
    # быть написаны неверно (Ооо → ООО, Ао → АО и т.д.)
    for org in _ORG_ABBREVS:
        result = re.sub(_ORG_BOUNDARY + org[0] + org[1:].lower() + _ORG_BOUNDARY_END, org, result)
        result = re.sub(_ORG_BOUNDARY + org.lower() + _ORG_BOUNDARY_END, org, result)
    return result

_SECTION_PREFIX_RE = re.compile(
    r'^(' + _SECTION_LABELS + r')\s*:\s*',
    re.IGNORECASE,
)

_QUALITY_ARTIFACTS = (
    re.compile(
        r'^\d+[\.\)]\s+(' + _SECTION_LABELS + r')',
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r'^(' + _SECTION_LABELS + r')\s*:',
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r'^Если\s+\w[\w_]*\s*[=:]', re.IGNORECASE | re.MULTILINE),
    re.compile(r'\*{2,}[^\*]+\*{2,}'),
    re.compile(r'\b(violation_type|has_photo|problem_type|damage_claim|night_calls|fine_number|gibdd_unit)\b'),
    re.compile(r'-{2,}'),  # двойное тире
    # Заголовок стоит раньше шапки — сигнал к retry
    re.compile(
        r'(?m)^\s*(ПРЕТЕНЗИЯ|ЖАЛОБА|ВОЗРАЖЕНИЕ|ЗАЯВЛЕНИЕ|ХОДАТАЙСТВО|УВЕДОМЛЕНИЕ)\s*\n'
        r'(?:.*\n)*?(?:Мировому|Начальнику|Руководителю|От\s*:)',
        re.IGNORECASE,
    ),
)


def clean_llm_text(text: str) -> str:
    """Deterministically removes GigaChat artifacts regardless of prompt.

    Handles:
    - Section labels and metadata
    - Post-title subtitles (≤60 chars)
    - Dates and signatures
    - All-caps lines (converts to normal case)
    - Markdown formatting
    - Duplicated titles
    """
    lines = text.split("\n")
    cleaned: list[str] = []
    prev_was_title = False
    title_seen = False

    for line in lines:
        s = line.strip()

        if not s:
            # Empty line: keep it, but don't reset prev_was_title
            # so post-title protection extends through empty lines
            cleaned.append(line)
            continue

        # Post-title subtitle removal: any line ≤60 chars after title
        # (except another title word, except numeric lines like "1. Something")
        if prev_was_title:
            if s[0].islower():
                continue
            if _TITLE_WITH_SUBTITLE_RE.match(s):
                continue
            if s not in _TITLE_WORDS and len(s) <= 60 and not s[0].isdigit():
                continue
            # If we got here, line is substantial enough to keep
            prev_was_title = False

        if s in _TITLE_WORDS:
            # First title word → keep. Duplicates → remove.
            if title_seen:
                continue
            title_seen = True
            prev_was_title = True
            cleaned.append(line)
            continue

        # "ПРЕТЕНЗИЯ о возврате..." → keep only title word
        m = _TITLE_WITH_SUBTITLE_RE.match(s)
        if m:
            if title_seen:
                continue
            title_seen = True
            cleaned.append(m.group(1).upper())
            prev_was_title = True
            continue

        prev_was_title = False

        # "Шапка: Руководителю..." → remove prefix, keep content
        m = _SECTION_PREFIX_RE.match(s)
        if m:
            remainder = s[m.end():].strip()
            if not remainder:
                continue
            line = line[len(s) - len(remainder):]
            s = remainder

        if _DATE_SIG_RE.match(s):
            continue
        if _SECTION_LABEL_RE.match(s):
            continue
        # Single section label word (without colon) → remove if it's a known label
        if s in _SECTION_LABELS.split('|') and not s.endswith(':'):
            continue
        if _CITY_LINE_RE.match(s):
            continue
        if _DOC_DATE_RE.match(s):
            continue
        if _SHORT_DATE_LINE_RE.match(s):
            continue
        if _MARKDOWN_RE.match(s):
            continue

        # ALL_CAPS lines (not a document title) → normal case
        # Properly: capitalize each word, handle patronymic names and multi-word phrases
        if _ALL_CAPS_RE.match(s) and len(s) > 15 and s not in _TITLE_WORDS:
            words_result = []
            for word in s.split():
                clean_word = re.sub(r'[«»"\']', '', word)
                if clean_word in _ORG_ABBREVS:
                    words_result.append(word)  # сохраняем как есть вместе с кавычками
                else:
                    words_result.append(word.capitalize())
            proper_case = " ".join(words_result)
            cleaned.append(line.replace(s, proper_case))
            continue

        # Title Case lines (GigaChat-артефакт) → sentence case
        if _is_title_case_line(s):
            cleaned.append(line.replace(s, _to_sentence_case(s)))
            continue

        # Remove markdown bold/italic inside lines
        # Don't touch signature block (_ / _)
        line = re.sub(r'\*{2,}([^\*]+)\*{2,}', r'\1', line)
        if not re.search(r'^_+\s*/\s*_+$', s):
            line = re.sub(r'_{2,}([^_]+)_{2,}', r'\1', line)

        # Fix inline ALL_CAPS words (e.g. "блокирован БАНКом" → "блокирован банком")
        # Don't apply to header lines (before title) — handled separately
        if title_seen and s not in _TITLE_WORDS:
            fixed = _fix_inline_caps(line.strip())
            line = line.replace(line.strip(), fixed) if fixed != line.strip() else line

        cleaned.append(line)

    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    # Capitalize первой буквы каждой строки шапки если она строчная
    # (GigaChat пишет адресные строки типа "московская обл." в нижнем регистре)
    result = re.sub(r'(?m)^([а-яёa-z])', lambda m: m.group(1).upper(), result)
    # Финальный pass: восстанавливаем аббревиатуры ООО/АО/ПАО/ГБУ независимо от регистра
    for org in _ORG_ABBREVS:
        result = re.sub(_ORG_BOUNDARY + org[0] + org[1:].lower() + _ORG_BOUNDARY_END, org, result)
        result = re.sub(_ORG_BOUNDARY + org.lower() + _ORG_BOUNDARY_END, org, result)
    return result


def fix_dashes(text: str) -> str:
    """Convert double/multiple dashes and en-dashes to em-dash (—).

    Should be called once at the very end of processing chain,
    after all other cleanup is done.
    """
    text = re.sub(r'-{2,}', '—', text)  # -- → —
    text = re.sub(r'–{2,}', '—', text)  # –– → —
    text = re.sub(r'[-–][-–]+', '—', text)  # смешанные
    # Одиночный дефис в начале строки как пункт перечисления → длинное тире
    text = re.sub(r'(?m)^- ', '— ', text)
    return text


def has_quality_artifacts(text: str) -> bool:
    """Check if text contains known quality issues that warrant retry."""
    return any(pattern.search(text) for pattern in _QUALITY_ARTIFACTS)
