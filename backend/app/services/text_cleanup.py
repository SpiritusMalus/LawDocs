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

_DATE_SIG_RE = re.compile(r'^(\d+[\.\)]?\s*)?дата\s+(и\s+)?подпись[:\.]?\s*$', re.IGNORECASE)

_CITY_LINE_RE = re.compile(r'^г\.\s+[А-ЯЁ][а-яё]+(,\s*\d{1,2}\s+\w+\s+\d{4}.*)?\.?\s*$')

_DOC_DATE_RE = re.compile(
    r'^\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|'
    r'июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\s*(г\.?|года)?\s*$',
    re.IGNORECASE,
)

_SHORT_DATE_LINE_RE = re.compile(r'^\d{1,2}\.\d{2}\.\d{4}\s*$')

_MARKDOWN_RE = re.compile(r'^#{1,3}\s|^\*{1,3}[^\*]|^-{3,}$')

_ALL_CAPS_RE = re.compile(r'^[А-ЯЁ\s\d\W]{10,}$')

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
    re.compile(r'\b(violation_type|has_photo|problem_type|damage_claim|night_calls)\b'),
)


def clean_llm_text(text: str) -> str:
    """Deterministically removes GigaChat artifacts regardless of prompt.

    Handles:
    - Section labels and metadata
    - Post-title subtitles (≤60 chars)
    - Dates and signatures
    - All-caps lines (converts to normal case)
    - Markdown formatting
    """
    lines = text.split("\n")
    cleaned: list[str] = []
    prev_was_title = False

    for line in lines:
        s = line.strip()

        if not s:
            prev_was_title = False
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

        if s in _TITLE_WORDS:
            prev_was_title = True
            cleaned.append(line)
            continue

        # "ПРЕТЕНЗИЯ о возврате..." → keep only title word
        m = _TITLE_WITH_SUBTITLE_RE.match(s)
        if m:
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
        if _CITY_LINE_RE.match(s):
            continue
        if _DOC_DATE_RE.match(s):
            continue
        if _SHORT_DATE_LINE_RE.match(s):
            continue
        if _MARKDOWN_RE.match(s):
            continue

        # ALL_CAPS lines (not a document title) → normal case
        # Properly: lowercase everything then capitalize first letter only
        if _ALL_CAPS_RE.match(s) and len(s) > 15 and s not in _TITLE_WORDS:
            proper_case = s.lower().capitalize()
            cleaned.append(line.replace(s, proper_case))
            continue

        # Remove markdown bold/italic inside lines
        # Don't touch signature block (_ / _)
        line = re.sub(r'\*{2,}([^\*]+)\*{2,}', r'\1', line)
        if not re.search(r'^_+\s*/\s*_+$', s):
            line = re.sub(r'_{2,}([^_]+)_{2,}', r'\1', line)

        cleaned.append(line)

    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result


def fix_dashes(text: str) -> str:
    """Convert double/multiple dashes to em-dash (—).

    Should be called once at the very end of processing chain,
    after all other cleanup is done.
    """
    return re.sub(r'-{2,}', '—', text)


def has_quality_artifacts(text: str) -> bool:
    """Check if text contains known quality issues that warrant retry."""
    return any(pattern.search(text) for pattern in _QUALITY_ARTIFACTS)
