"""Страховка от рассинхрона опций wizard и словарей юр-секций калькуляторов.

Баг-паттерн (handoff_127/128): radio-опция есть в YAML-конфиге, но ключа в
словаре секций калькулятора нет → документ молча получает fallback. Если
fallback = конкретная ветка (чужая статья закона) — это юр-брак (напр. shop
с problem_type=other получал ст.18 о дефектах; employer dismissal — текст про
зарплату).

Тест проверяет инвариант: для неизвестной опции legal-секция НЕ должна совпадать
ни с одной из конкретных веток словаря (т.е. fallback обязан быть нейтральным),
и сырой код опции не должен утекать в текст документа.
"""
import inspect
import re
from pathlib import Path

import pytest

import app.services.calculators as C
from app.situations.registry import CONTACT_STEP, registry
from app.services.field_resolve import _FIELD_ALIASES

CONFIGS_DIR = Path(__file__).parent.parent / "app" / "situations" / "configs"


@pytest.fixture(scope="module", autouse=True)
def _load():
    registry.load(CONFIGS_DIR)


def _all_situation_ids() -> list[str]:
    """ID всех ситуаций для parametrize (registry грузится на этапе коллекции)."""
    if not len(registry):
        registry.load(CONFIGS_DIR)
    return sorted(registry.ids())


def _options(situation_id: str, field_id: str) -> list[str]:
    cfg = registry.get(situation_id)
    assert cfg is not None, f"нет конфига {situation_id}"
    for step in cfg.wizard_steps:
        for f in step.fields:
            if f.id == field_id and f.options:
                return [o.value for o in f.options]
    raise AssertionError(f"нет radio-поля {field_id} в {situation_id}")


# (ситуация, поле, словарь конкретных юр-секций, имя выходного ключа калькулятора)
# Поле определяет legal-секцию через словарь; неизвестная опция должна давать
# нейтральный fallback, не равный ни одной ветке словаря.
LEGAL_DICT_CASES = [
    ("shop", "problem_type", C._SHOP_LEGAL_SECTIONS, "calculated_legal_section"),
    ("telecom", "problem_type", C._TELECOM_LEGAL_SECTIONS, "calculated_legal_section"),
    ("employer", "violation_type", C._EMPLOYER_LEGAL_SECTIONS, "calculated_legal_section"),
    ("auto_repair", "violation_type", C._AUTO_REPAIR_LEGAL_SECTIONS, "calculated_legal_section"),
    ("airline", "violation_type", C._AIRLINE_LEGAL_SECTIONS, "calculated_legal_section"),
]


@pytest.mark.parametrize("sid,field_id,legal_dict,out_key", LEGAL_DICT_CASES)
def test_unknown_option_uses_neutral_fallback(sid, field_id, legal_dict, out_key):
    """Неизвестная опция не должна получать текст конкретной ветки (чужую статью)."""
    calc = C.SITUATION_CALCULATORS[sid]
    result = calc({field_id: "__unknown_option__"})
    legal = result.get(out_key) or ""
    assert legal, f"{sid}: пустая legal-секция при неизвестной опции"
    # fallback не должен совпадать ни с одной конкретной веткой словаря
    for key, branch_text in legal_dict.items():
        assert legal != branch_text, (
            f"{sid}.{field_id}: неизвестная опция получила ветку '{key}' "
            f"(молчаливый fallback на чужую статью)"
        )


@pytest.mark.parametrize("sid,field_id,legal_dict,out_key", LEGAL_DICT_CASES)
def test_every_option_has_branch_or_neutral_fallback(sid, field_id, legal_dict, out_key):
    """Каждая реальная опция YAML либо имеет свою ветку, либо нейтральный fallback
    (не текст другой ветки)."""
    calc = C.SITUATION_CALCULATORS[sid]
    for value in _options(sid, field_id):
        legal = calc({field_id: value}).get(out_key) or ""
        if value in legal_dict:
            continue  # своя ветка — ок
        # опция без ветки (напр. other, dismissal) → fallback не должен быть чужой веткой
        for key, branch_text in legal_dict.items():
            assert legal != branch_text, (
                f"{sid}.{field_id}={value}: нет своей ветки, fallback взял ветку "
                f"'{key}' — нужен нейтральный текст или своя ветка"
            )


# ── Архитектурный инвариант: нет «мёртвых» полей ──────────────────────────
# Первопричина мёртвых полей (handoff: рассинхрон копипасты) — поле объявлено в
# wizard, но никто его не читает. Поле «используется», если встречается в одном
# из 5 мест: header_fields, narrative_fields, плейсхолдер [поле] в python_template
# или system_prompt, либо data.get("поле")/data["поле"] в калькуляторе ситуации.

# Контактные поля добавляются ко всем ситуациям через CONTACT_STEP и читаются
# в шапке через алиасы (field_resolve) — их не считаем «объявленными в ситуации».
_CONTACT_FIELD_IDS = {f.id for f in CONTACT_STEP.fields}

# Все имена-алиасы контактов (full_name↔user_full_name и т.п.) — header_fields
# могут ссылаться на любой вариант.
_ALIAS_NAMES = {name for variants in _FIELD_ALIASES.values() for name in variants}

_PLACEHOLDER_RE = re.compile(r"\[([a-z_][a-z0-9_]*)\]")
_CALC_READ_RE = re.compile(r"""\bdata(?:\.get\(|\[)["']([a-z_][a-z0-9_]*)["']""")
_FORM_READ_RE = re.compile(r"""\bform_data(?:\.get\(|\[)["']([a-z_][a-z0-9_]*)["']""")


def _used_field_ids(config) -> set[str]:
    """Поля, которые ситуация реально потребляет (5 путей)."""
    used: set[str] = set()

    # 1. header_fields (+ алиасы контактов)
    for hf in config.header_fields:
        used.add(hf.field)
        for canonical, variants in _FIELD_ALIASES.items():
            if hf.field in variants or hf.field == canonical:
                used.update(variants)
                used.add(canonical)

    # 2. narrative_fields
    used.update(config.narrative_fields)

    # 2b. legal_refs_by_branch: ключи формата "field:value" выбирают нормы по полю
    for branch_key in config.legal_refs_by_branch:
        used.add(branch_key.split(":", 1)[0])

    # 3-4. плейсхолдеры [поле] в python_template и system_prompt
    for text in (config.python_template, config.system_prompt):
        if text:
            used.update(_PLACEHOLDER_RE.findall(text))

    # 5. data.get("x")/data["x"]/form_data... в калькуляторе ситуации
    calc = C.SITUATION_CALCULATORS.get(config.id)
    if calc is not None:
        src = inspect.getsource(calc)
        used.update(_CALC_READ_RE.findall(src))
        used.update(_FORM_READ_RE.findall(src))

    return used


@pytest.mark.parametrize("sid", _all_situation_ids())
def test_no_dead_wizard_fields(sid):
    """Каждое объявленное в wizard поле где-то потребляется (нет мёртвых полей).

    Ловит рассинхрон копипасты: поле перенесли в YAML, но не подключили к
    калькулятору/шапке/нарративу/шаблону этой ситуации. Юзер вводит данные впустую.
    """
    config = registry.get(sid)
    declared = {
        f.id
        for step in config.wizard_steps
        for f in step.fields
        if f.id not in _CONTACT_FIELD_IDS
    }
    used = _used_field_ids(config) | _ALIAS_NAMES  # контакты-алиасы всегда «используются» в шапке
    dead = declared - used
    assert not dead, (
        f"{sid}: объявлены, но нигде не используются (мёртвые поля): {sorted(dead)}. "
        f"Подключите к калькулятору/header_fields/narrative_fields/шаблону — или удалите из wizard."
    )


def test_ddu_termination_other_no_raw_code_or_dangling():
    """ddu_termination: 'other' не должен давать пустую строку (повисший предлог
    «в связи с ») или сырой код в тексте основания."""
    calc = C.SITUATION_CALCULATORS["ddu_termination"]
    for value in _options("ddu_termination", "termination_reason"):
        text = calc({"termination_reason": value}).get("termination_reason_text") or ""
        assert text.strip(), f"ddu_termination={value}: пустой termination_reason_text"
        assert value not in text.split(), (
            f"ddu_termination={value}: сырой код опции утёк в текст"
        )
