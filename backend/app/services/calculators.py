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


def calculate_dtp_osago(form_data: dict) -> dict:
    """Претензия в страховую по ОСАГО: пеня ст. 16.1 ч.21 ФЗ-40 + недоплата."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_underpayment_section"] = ""
    data["calculated_claim_amount"] = ""
    data["calculated_overdue_days"] = ""
    data["calculated_penalty"] = ""

    violation = str(data.get("violation_type", ""))

    try:
        damage = Decimal(str(data["damage_amount"]))
    except Exception:
        return data

    try:
        paid = Decimal(str(data.get("paid_amount") or "0"))
    except Exception:
        paid = Decimal("0")

    # Underpayment (underestimate branch)
    if violation == "underestimate":
        underpayment = max(damage - paid, Decimal("0"))
        data["calculated_underpayment"] = _fmt(underpayment)
        data["calculated_underpayment_section"] = (
            f"Страховая компания выплатила {_fmt(paid)} руб., "
            f"тогда как ущерб составляет {_fmt(damage)} руб. "
            f"Недоплата: {_fmt(underpayment)} руб."
        )
        claim_base = underpayment
    else:
        claim_base = max(damage - paid, Decimal("0"))

    data["calculated_claim_amount"] = _fmt(claim_base)

    # Penalty: claim_base × 1% × overdue_days (ст. 16.1 ч.21 ФЗ-40)
    # 20 рабочих дней ≈ 28 календарных дней
    claim_date = _parse_date(data.get("claim_date"))
    if claim_date:
        due_date = claim_date + timedelta(days=28)
        overdue_days = max((date.today() - due_date).days, 0)
        data["calculated_overdue_days"] = str(overdue_days)
        if overdue_days > 0:
            penalty = claim_base * Decimal("0.01") * Decimal(overdue_days)
            data["calculated_penalty"] = _fmt(penalty)
            data["calculated_penalty_section"] = (
                f"Пеня по ст. 16.1 ч. 21 ФЗ-40: {_fmt(claim_base)} руб. × 1% × "
                f"{overdue_days} дней (просрочка с {_fmt_date_ru(due_date)}) "
                f"= {_fmt(penalty)} руб."
            )

    return data


_CB_RATE = Decimal("21")


def calculate_employer(form_data: dict) -> dict:
    """Претензия работодателю: компенсация 1/150 × ставки ЦБ за каждый день задержки (ст. 236 ТК РФ)."""
    data = dict(form_data)
    data["calculated_compensation_section"] = ""
    data["calculated_compensation"] = ""

    last_paid = _parse_date(data.get("last_payment_date"))
    if not last_paid:
        return data
    delay_days = max((date.today() - last_paid).days, 0)
    if delay_days == 0:
        return data

    try:
        debt = Decimal(str(data["debt_amount"]))
        compensation = debt * Decimal("1") / Decimal("150") * _CB_RATE / Decimal("100") * Decimal(delay_days)
        compensation = compensation.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return data

    data["calculated_delay_days"] = str(delay_days)
    data["calculated_compensation"] = _fmt(compensation)
    total = debt + compensation
    data["calculated_compensation_section"] = (
        f"Компенсация за задержку {delay_days} дней: "
        f"{_fmt(debt)} руб. × 1/150 × {_CB_RATE}% × {delay_days} дней = "
        f"{_fmt(compensation)} руб. (ст. 236 ТК РФ). "
        f"Итого к выплате: {_fmt(debt)} + {_fmt(compensation)} = {_fmt(total)} руб."
    )
    return data


def calculate_repair(form_data: dict) -> dict:
    """Претензия подрядчику: неустойка 3%/день от даты обнаружения недостатков (ст. 28 ч. 5 ЗоЗПП)."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_penalty"] = ""

    discovery = _parse_date(data.get("defect_discovery_date"))
    if not discovery:
        return data
    delay_days = max((date.today() - discovery).days, 0)

    try:
        price = Decimal(str(data["work_price"]))
        penalty = min(price * Decimal("0.03") * Decimal(delay_days), price)
    except Exception:
        return data

    data["calculated_penalty_days"] = str(delay_days)
    data["calculated_penalty"] = _fmt(penalty)
    data["calculated_penalty_section"] = (
        f"За {delay_days} дней с момента обнаружения недостатков "
        f"неустойка составляет {_fmt(penalty)} руб. "
        f"(3% × {_fmt(price)} руб. × {delay_days} дней, не более стоимости работ, "
        f"ст. 28 ч. 5 ЗоЗПП)."
    )
    return data


def calculate_insurance(form_data: dict) -> dict:
    """Претензия в страховую: недоплата + пеня 1%/день (ОСАГО ст. 16.1 ФЗ-40 / КАСКО ЗоЗПП ст. 28)."""
    data = dict(form_data)
    data["calculated_underpayment_section"] = ""
    data["calculated_penalty_section"] = ""
    data["calculated_underpayment"] = ""
    data["calculated_total"] = ""

    try:
        actual = Decimal(str(data["actual_damage"]))
    except Exception:
        return data

    try:
        paid = Decimal(str(data.get("paid_amount") or "0"))
    except Exception:
        paid = Decimal("0")

    underpayment = max(actual - paid, Decimal("0"))
    if underpayment > 0:
        data["calculated_underpayment"] = _fmt(underpayment)
        data["calculated_underpayment_section"] = (
            f"Страховая компания выплатила {_fmt(paid)} руб., "
            f"тогда как реальный ущерб составляет {_fmt(actual)} руб. "
            f"Недоплата: {_fmt(underpayment)} руб."
        )

    try:
        overdue_days = int(str(data.get("overdue_days") or "0"))
    except Exception:
        overdue_days = 0

    if overdue_days > 0 and underpayment > 0:
        penalty = underpayment * Decimal("0.01") * Decimal(overdue_days)
        total = underpayment + penalty
        data["calculated_penalty"] = _fmt(penalty)
        data["calculated_total"] = _fmt(total)
        data["calculated_penalty_section"] = (
            f"Неустойка: {_fmt(underpayment)} руб. × 1% × {overdue_days} дней = "
            f"{_fmt(penalty)} руб. "
            f"Итого к выплате: {_fmt(underpayment)} + {_fmt(penalty)} = {_fmt(total)} руб."
        )
    elif underpayment > 0:
        data["calculated_total"] = _fmt(underpayment)

    return data


def calculate_telecom(form_data: dict) -> dict:
    """Претензия провайдеру: возврат пропорционально периоду отсутствия услуги (monthly_fee / 30 × дней)."""
    data = dict(form_data)
    data["calculated_refund_section"] = ""

    problem_type = str(data.get("problem_type", ""))
    if problem_type not in ("no_service", "slow_speed"):
        return data

    start = _parse_date(data.get("problem_start_date"))
    if not start:
        return data
    days = max((date.today() - start).days, 0)

    try:
        monthly = Decimal(str(data["monthly_fee"]))
        if monthly <= 0:
            return data
        refund = (monthly / Decimal("30") * Decimal(days)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except Exception:
        return data

    data["calculated_refund_days"] = str(days)
    data["calculated_refund"] = _fmt(refund)
    data["calculated_refund_section"] = (
        f"За {days} дней отсутствия услуги сумма к возврату: "
        f"{_fmt(monthly)} руб. / 30 × {days} дней = {_fmt(refund)} руб."
    )
    return data


def calculate_airline(form_data: dict) -> dict:
    """Претензия авиакомпании: компенсация за задержку 25 руб./час + штраф 50% (ВК РФ ст. 120)."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""

    try:
        ticket = Decimal(str(data["ticket_price"]))
    except Exception:
        return data

    try:
        delay_hours = int(str(data.get("delay_hours") or "0"))
    except Exception:
        delay_hours = 0

    try:
        extra = Decimal(str(data.get("extra_expenses") or "0"))
    except Exception:
        extra = Decimal("0")

    try:
        received = Decimal(str(data.get("received_compensation") or "0"))
    except Exception:
        received = Decimal("0")

    parts = []
    total = Decimal("0")

    if delay_hours > 0:
        delay_comp = Decimal("25") * Decimal(delay_hours)
        fine = (ticket * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += delay_comp + fine
        parts.append(
            f"компенсация за задержку {delay_hours} ч: 25 × {delay_hours} = {_fmt(delay_comp)} руб.; "
            f"штраф 50% от стоимости билета: {_fmt(fine)} руб."
        )
        data["calculated_delay_comp"] = _fmt(delay_comp)
        data["calculated_fine"] = _fmt(fine)

    if extra > 0:
        total += extra
        parts.append(f"доп. расходы: {_fmt(extra)} руб.")

    if not parts:
        return data

    if received > 0:
        total = max(total - received, Decimal("0"))
        parts.append(f"уже выплачено: −{_fmt(received)} руб.")

    data["calculated_total"] = _fmt(total)
    data["calculated_penalty_section"] = (
        "; ".join(parts) + f". Итого к выплате: {_fmt(total)} руб."
    )
    return data


SITUATION_CALCULATORS: dict[str, callable] = {
    "ddu_delay": calculate_ddu_delay,
    "ddu_termination": calculate_ddu_termination,
    "shop": calculate_shop,
    "auto_repair": calculate_auto_repair,
    "gym_refund": calculate_gym_refund,
    "dtp_osago": calculate_dtp_osago,
    "employer": calculate_employer,
    "repair": calculate_repair,
    "insurance": calculate_insurance,
    "telecom": calculate_telecom,
    "airline": calculate_airline,
}
