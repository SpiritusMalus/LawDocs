"""
Pre-LLM calculators for situations that require deterministic math.

Each calculator receives form_data and returns a new dict with injected
`calculated_*` fields that the system_prompt can reference directly.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def _fmt(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _ddu_neustoyka(price: Decimal, rate: Decimal, days: int) -> Decimal:
    """ФЗ-214 ст. 6 ч. 2: 1/150 ставки ЦБ × цена × дни (для граждан)."""
    return price * rate / Decimal("100") / Decimal("150") * Decimal(days)


def calculate_ddu_delay(form_data: dict) -> dict:
    """Претензия за просрочку передачи квартиры по ДДУ."""
    data = dict(form_data)
    planned = _parse_date(data.get("planned_transfer_date"))
    actual = _parse_date(data.get("actual_transfer_date")) or date.today()
    if not planned:
        return data
    delay_days = max((actual - planned).days, 0)
    try:
        price = Decimal(str(data["contract_price"]))
        rate = Decimal(str(data["cb_rate"]))
        neustoyka = _ddu_neustoyka(price, rate, delay_days)
    except Exception:
        return data
    data["calculated_delay_days"] = str(delay_days)
    data["calculated_neustoyka"] = _fmt(neustoyka)
    return data


def calculate_ddu_termination(form_data: dict) -> dict:
    """Расторжение ДДУ: возврат цены + 1/150 ставки за каждый день (ФЗ-214 ст. 9 ч. 2)."""
    data = dict(form_data)
    paid = _parse_date(data.get("payment_date"))
    if not paid:
        return data
    days_used = max((date.today() - paid).days, 0)
    try:
        price = Decimal(str(data["contract_price"]))
        rate = Decimal(str(data["cb_rate"]))
        interest = _ddu_neustoyka(price, rate, days_used)
        total = price + interest
    except Exception:
        return data
    data["calculated_days_used"] = str(days_used)
    data["calculated_interest"] = _fmt(interest)
    data["calculated_total_return"] = _fmt(total)
    return data


SITUATION_CALCULATORS: dict[str, callable] = {
    "ddu_delay": calculate_ddu_delay,
    "ddu_termination": calculate_ddu_termination,
}
