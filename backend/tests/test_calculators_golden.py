"""Золотой тест: вывод калькуляторов не должен меняться при рефакторе.

Это защитная сеть для M3. Если этот тест упал — значит рефактор изменил суммы или
текст статей закона в платных документах. Менять `calculators_golden.json` можно
ТОЛЬКО осознанно (когда меняется само законодательство/формула), отдельным коммитом
с явным обоснованием.
"""

import json

from tests._calc_golden_lib import GOLDEN_PATH, compute_golden

_EXPECTED = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
_ACTUAL = compute_golden()


def test_all_situations_present():
    assert set(_ACTUAL) == set(_EXPECTED), "набор калькуляторов разошёлся с золотым снимком"


def test_calculator_outputs_match_golden():
    diffs = []
    for sid in sorted(_EXPECTED):
        if _ACTUAL.get(sid) != _EXPECTED[sid]:
            diffs.append(sid)
    assert not diffs, (
        "вывод калькуляторов изменился (суммы/текст статей) для: "
        + ", ".join(diffs)
        + ". Если это намеренно — обнови golden отдельным коммитом."
    )
