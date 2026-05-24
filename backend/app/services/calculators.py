"""
Pre-LLM calculators for situations that require deterministic math.

Each calculator receives form_data and returns a new dict with injected
`calculated_*` fields that the system_prompt can reference directly.
"""

import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

_MONTHS_GENITIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

_DDU_TERMINATION_REASON_TEXTS = {
    # Творительный падеж — используется после «в связи с»
    "delay_2months": (
        "нарушением предусмотренного договором срока передачи объекта долевого "
        "строительства более чем на два месяца (п. 1 ч. 1 ст. 9 Федерального "
        "закона № 214-ФЗ)"
    ),
    "defects_major": (
        "существенным нарушением требований к качеству объекта долевого "
        "строительства (п. 2 ч. 1 ст. 9 Федерального закона № 214-ФЗ)"
    ),
    "construction_stopped": (
        "прекращением или приостановлением строительства многоквартирного дома "
        "при наличии обстоятельств, очевидно свидетельствующих о том, что в "
        "предусмотренный договором срок объект долевого строительства не будет "
        "передан участнику долевого строительства (п. 3 ч. 1 ст. 9 Федерального "
        "закона № 214-ФЗ)"
    ),
    "other": "",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def _fmt(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _fmt_date_ru(d: date) -> str:
    return f"{d.day} {_MONTHS_GENITIVE[d.month - 1]} {d.year} года"


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

    # Текст основания расторжения для python_template
    reason_code = str(data.get("termination_reason", ""))
    data["termination_reason_text"] = _DDU_TERMINATION_REASON_TEXTS.get(reason_code, reason_code)

    # Форматированные даты для подстановки в python_template
    contract_d = _parse_date(data.get("contract_date"))
    paid = _parse_date(data.get("payment_date"))
    if contract_d:
        data["formatted_contract_date"] = _fmt_date_ru(contract_d)
    if paid:
        data["formatted_payment_date"] = _fmt_date_ru(paid)

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


def calculate_shop(form_data: dict) -> dict:
    """Претензия в магазин: неустойка 1%/день по ст. 23 ЗоЗПП."""
    data = dict(form_data)
    start = _parse_date(data.get("penalty_start_date")) or _parse_date(data.get("appeal_date"))
    if not start:
        data["calculated_penalty_section"] = ""
        return data
    delay_days = max((date.today() - start).days, 0)
    try:
        price = Decimal(str(data["product_price"]))
        penalty = min(price * Decimal("0.01") * Decimal(delay_days), price)
    except Exception:
        data["calculated_penalty_section"] = ""
        return data
    data["calculated_penalty_days"] = str(delay_days)
    data["calculated_penalty"] = _fmt(penalty)
    data["calculated_penalty_section"] = (
        f"За {delay_days} дней просрочки исполнения требования "
        f"неустойка составляет {_fmt(penalty)} руб. "
        f"(не более стоимости товара, ст. 23 ЗоЗПП)."
    )
    return data


def calculate_auto_repair(form_data: dict) -> dict:
    """Претензия в автосервис: ветки по violation_type (delay / bad_quality / overcharge)."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_overcharge_section"] = ""

    violation = str(data.get("violation_type", ""))

    if violation == "delay":
        planned = _parse_date(data.get("planned_date"))
        if planned:
            delay_days = max((date.today() - planned).days, 0)
            try:
                price = Decimal(str(data["work_price"]))
                penalty = min(price * Decimal("0.03") * Decimal(delay_days), price)
                data["calculated_delay_days"] = str(delay_days)
                data["calculated_penalty"] = _fmt(penalty)
                data["calculated_penalty_section"] = (
                    f"За {delay_days} дней просрочки выдачи автомобиля "
                    f"неустойка составляет {_fmt(penalty)} руб. "
                    f"(3% × стоимость работ × дни, не более стоимости работ, "
                    f"ст. 28 ч. 5 ЗоЗПП)."
                )
            except Exception:
                pass

    elif violation == "overcharge":
        try:
            work = Decimal(str(data["work_price"]))
            agreed = Decimal(str(data["agreed_price"]))
            diff = max(work - agreed, Decimal("0"))
            data["calculated_overcharge_diff"] = _fmt(diff)
            data["calculated_overcharge_section"] = (
                f"Цена в договоре составляла {_fmt(agreed)} руб., "
                f"фактически выставлен счёт на {_fmt(work)} руб. "
                f"Разница {_fmt(diff)} руб. — незаконное завышение цены "
                f"(ст. 709 ГК РФ, ст. 16 ЗоЗПП)."
            )
        except Exception:
            pass

    return data


_PERIOD_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:месяц(?:ев|а)?|month)", re.IGNORECASE), lambda m: int(m.group(1)) * 30),
    (re.compile(r"(\d+)\s*(?:год(?:а)?|лет|year)", re.IGNORECASE), lambda m: int(m.group(1)) * 365),
    (re.compile(r"(\d+)\s*(?:недел(?:и|ь|я)|week)", re.IGNORECASE), lambda m: int(m.group(1)) * 7),
    (re.compile(r"(\d+)\s*(?:дней|дня|день|day)", re.IGNORECASE), lambda m: int(m.group(1))),
]
_DATE_RANGE_RE = re.compile(
    r"с?\s*(\d{2})\.(\d{2})\.(\d{4})\s*(?:по|—|-)\s*(\d{2})\.(\d{2})\.(\d{4})"
)


def _parse_subscription_days(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip()
    m = _DATE_RANGE_RE.search(text)
    if m:
        try:
            start = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            end = date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
            return max((end - start).days, 0)
        except Exception:
            pass
    for pattern, extractor in _PERIOD_PATTERNS:
        hit = pattern.search(text)
        if hit:
            return extractor(hit)
    return None


def calculate_gym_refund(form_data: dict) -> dict:
    """Фитнес-клуб: возврат за неиспользованный период абонемента (ст. 32 ЗоЗПП)."""
    data = dict(form_data)
    data["calculated_refund_section"] = ""
    data["calculated_refund_amount"] = ""

    # Пользователь указал сумму вручную — используем её напрямую
    try:
        user_amount = Decimal(str(data["refund_amount"]))
        if user_amount > 0:
            data["calculated_refund_amount"] = _fmt(user_amount)
            data["calculated_refund_section"] = (
                f"Сумма к возврату за неиспользованный период: "
                f"{_fmt(user_amount)} руб."
            )
            return data
    except Exception:
        pass

    # Рассчитываем пропорционально
    purchase = _parse_date(data.get("purchase_date"))
    refund_request = _parse_date(data.get("refund_request_date")) or date.today()
    total_days = _parse_subscription_days(data.get("subscription_period"))

    if not purchase or not total_days or total_days <= 0:
        return data

    end_date = purchase + timedelta(days=total_days)
    unused_days = max((end_date - refund_request).days, 0)

    try:
        price = Decimal(str(data["subscription_price"]))
        refund = (price / Decimal(total_days) * Decimal(unused_days)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except Exception:
        return data

    data["calculated_total_days"] = str(total_days)
    data["calculated_unused_days"] = str(unused_days)
    data["calculated_refund_amount"] = _fmt(refund)
    data["calculated_refund_section"] = (
        f"Расчёт суммы к возврату: "
        f"{_fmt(price)} руб. / {total_days} дней × {unused_days} дней = "
        f"{_fmt(refund)} руб."
    )
    return data


SITUATION_CALCULATORS: dict[str, callable] = {
    "ddu_delay": calculate_ddu_delay,
    "ddu_termination": calculate_ddu_termination,
    "shop": calculate_shop,
    "auto_repair": calculate_auto_repair,
    "gym_refund": calculate_gym_refund,
}
