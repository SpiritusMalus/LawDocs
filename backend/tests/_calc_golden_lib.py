"""Золотые тесты калькуляторов: заморозка «сегодня» + синтез входов из wizard-конфигов.

Назначение — характеризующий (golden) снимок ВЫВОДА всех калькуляторов. Рефактор
M3 обязан быть byte-identical по выводу: суммы и тексты статей закона не должны
измениться. Снимок генерируется до рефактора (`generate_golden.py`), коммитится,
и `test_calculators_golden.py` сверяет с ним живой код.

Дата заморожена, потому что калькуляторы считают просрочку от date.today(): без
заморозки снимок «протухал» бы каждый день.
"""

import datetime as _dt
from pathlib import Path

from app.services import calculators
from app.situations.registry import registry

# Фиксированное «сегодня» для детерминизма снимка.
FIXED_TODAY = _dt.date(2025, 6, 1)

_CONFIGS_DIR = Path(calculators.__file__).resolve().parent.parent / "situations" / "configs"


class _FrozenDate(_dt.date):
    @classmethod
    def today(cls) -> _dt.date:
        return _dt.date(FIXED_TODAY.year, FIXED_TODAY.month, FIXED_TODAY.day)


class _FrozenDateTime(_dt.datetime):
    @classmethod
    def now(cls, tz=None) -> _dt.datetime:
        return _dt.datetime(FIXED_TODAY.year, FIXED_TODAY.month, FIXED_TODAY.day, tzinfo=tz)

    @classmethod
    def today(cls) -> _dt.datetime:
        return cls.now()


def _ensure_registry_loaded() -> None:
    if len(registry) == 0:
        registry.load(_CONFIGS_DIR)


def _synth_value(field) -> str:
    """Детерминированное значение поля по типу — для характеризующего прогона."""
    if field.type == "number":
        fid = field.id.lower()
        if any(k in fid for k in ("hour", "day", "count", "qty", "num", "people", "passenger")):
            return "5"
        return "100000"
    if field.type == "date":
        return "01.01.2025"
    if field.type == "radio":
        return field.options[0].value if field.options else ""
    return "Тест"


def _synth_cases(config) -> list[tuple[str, dict]]:
    """База (первый вариант каждого radio) + по кейсу на каждый вариант radio.

    Перебор вариантов radio покрывает ветки выбора статьи/требования — именно там
    живёт юридический текст, который рефактор не должен сдвинуть.
    """
    fields = [f for step in config.wizard_steps for f in step.fields]
    base = {f.id: _synth_value(f) for f in fields}
    cases = [("base", dict(base))]
    for f in fields:
        if f.type == "radio" and f.options and len(f.options) > 1:
            for opt in f.options:
                variant = dict(base)
                variant[f.id] = opt.value
                cases.append((f"{f.id}={opt.value}", variant))
    return cases


def compute_golden() -> dict:
    """Прогоняет все калькуляторы с замороженной датой и возвращает снимок вывода."""
    _ensure_registry_loaded()
    orig_date, orig_datetime = calculators.date, calculators.datetime
    calculators.date, calculators.datetime = _FrozenDate, _FrozenDateTime
    try:
        snapshot: dict = {}
        for sid, fn in sorted(calculators.SITUATION_CALCULATORS.items()):
            config = registry.get(sid)
            cases = _synth_cases(config) if config else [("base", {})]
            entries = []
            for label, inp in cases:
                try:
                    out = fn(dict(inp))
                    changed = {
                        k: out[k] for k in sorted(out) if k not in inp or out[k] != inp.get(k)
                    }
                    entries.append({"label": label, "output": changed})
                except Exception as e:  # noqa: BLE001 — снимок фиксирует и ошибочный путь
                    entries.append({"label": label, "error": f"{type(e).__name__}: {e}"})
            snapshot[sid] = entries
        return snapshot
    finally:
        calculators.date, calculators.datetime = orig_date, orig_datetime


GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "calculators_golden.json"
