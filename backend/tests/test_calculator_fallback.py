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
from pathlib import Path

import pytest

import app.services.calculators as C
from app.situations.registry import registry

CONFIGS_DIR = Path(__file__).parent.parent / "app" / "situations" / "configs"


@pytest.fixture(scope="module", autouse=True)
def _load():
    registry.load(CONFIGS_DIR)


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
