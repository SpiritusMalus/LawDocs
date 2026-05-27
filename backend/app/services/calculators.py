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
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    developer = str(data.get("developer_name") or "").strip()
    contract_number = str(data.get("contract_number") or "").strip()
    contract_date = str(data.get("contract_date") or "").strip()
    apartment_address = str(data.get("apartment_address") or "").strip()

    # Intro
    intro = "Между мной и застройщиком"
    if developer:
        intro = f"Между мной и {developer}"
    if contract_number:
        intro += f" заключён договор участия в долевом строительстве № {contract_number}"
    else:
        intro += " заключён договор участия в долевом строительстве"
    if contract_date:
        intro += f" от {contract_date}"
    if apartment_address:
        intro += f". Объект долевого строительства: {apartment_address}"
    intro += "."
    data["calculated_intro_section"] = intro

    planned = _parse_date(data.get("planned_transfer_date"))
    actual = _parse_date(data.get("actual_transfer_date")) or date.today()
    if not planned:
        return data
    delay_days = max((actual - planned).days, 0)

    planned_str = str(data.get("planned_transfer_date") or "").strip()
    actual_str = str(data.get("actual_transfer_date") or "").strip()
    if actual_str:
        viol = (
            f"Согласно договору квартира должна была быть передана {planned_str}. "
            f"Фактически квартира передана {actual_str}. "
            f"Просрочка составила {delay_days} дн."
        )
    else:
        viol = (
            f"Согласно договору квартира должна была быть передана {planned_str}. "
            f"По состоянию на дату составления настоящей претензии квартира не передана. "
            f"Просрочка составляет {delay_days} дн."
        )
    data["calculated_violation_section"] = viol

    data["calculated_legal_section"] = (
        "В соответствии с частью 2 статьи 6 Федерального закона от 30.12.2004 "
        "№ 214-ФЗ «Об участии в долевом строительстве» в случае нарушения "
        "предусмотренного договором срока передачи объекта долевого строительства "
        "застройщик уплачивает участнику долевого строительства неустойку в размере "
        "одной сто пятидесятой ставки рефинансирования Центрального банка РФ, "
        "действующей на день исполнения обязательства, от цены договора за каждый "
        "день просрочки. В силу пункта 6 статьи 13 Закона РФ от 07.02.1992 № 2300-1 "
        "«О защите прав потребителей» при удовлетворении судом требований потребителя "
        "с застройщика взыскивается штраф в размере пятидесяти процентов от суммы, "
        "присуждённой потребителю."
    )

    try:
        price = Decimal(str(data["contract_price"]))
        rate = Decimal(str(data["cb_rate"]))
        neustoyka = _ddu_neustoyka(price, rate, delay_days)
    except Exception:
        return data

    data["calculated_delay_days"] = str(delay_days)
    data["calculated_neustoyka"] = _fmt(neustoyka)

    data["calculated_amount_section"] = (
        f"Расчёт неустойки: {_fmt(price)} руб. × {rate}% / 100 / 150 × "
        f"{delay_days} дн. = {_fmt(neustoyka)} руб."
    )

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу выплатить неустойку в размере "
        f"{_fmt(neustoyka)} руб. в течение десяти календарных дней с даты получения "
        f"настоящей претензии."
        + (
            " Прошу также передать объект долевого строительства в разумный срок."
            if not actual_str else ""
        )
        + " В случае неисполнения требования в добровольном порядке буду вынужден(-а) "
        "обратиться с иском в суд, а также с жалобой в Роспотребнадзор и "
        "Министерство строительства и жилищно-коммунального хозяйства РФ."
    )

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


_AUTO_REPAIR_VIOLATION_SECTIONS = {
    "bad_quality": (
        "Автосервис выполнил работу некачественно: после возврата автомобиля "
        "были выявлены недостатки, свидетельствующие о ненадлежащем исполнении "
        "договора возмездного оказания услуг."
    ),
    "delay": (
        "Автосервис нарушил срок выдачи автомобиля: по условиям договора "
        "автомобиль должен был быть возвращён в оговорённую дату, "
        "однако по состоянию на дату настоящей претензии выдан не был."
    ),
    "overcharge": (
        "Автосервис в одностороннем порядке завысил стоимость работ: "
        "выставленный счёт превышает первоначально согласованную цену "
        "без письменного согласия заказчика."
    ),
}

_AUTO_REPAIR_LEGAL_SECTIONS = {
    "bad_quality": (
        "В соответствии с пунктом 1 статьи 29 Закона РФ от 07.02.1992 № 2300-1 "
        "«О защите прав потребителей» при обнаружении недостатков выполненной "
        "работы потребитель вправе потребовать безвозмездного устранения "
        "недостатков выполненной работы, уменьшения цены выполненной работы "
        "либо возмещения понесённых им расходов. На основании статей 722 и 723 "
        "Гражданского кодекса РФ подрядчик несёт ответственность за ненадлежащее "
        "качество работ в течение гарантийного срока, а при его отсутствии — "
        "в течение двух лет с момента передачи результата работ."
    ),
    "delay": (
        "В соответствии с пунктом 5 статьи 28 Закона РФ от 07.02.1992 № 2300-1 "
        "«О защите прав потребителей» в случае нарушения установленных сроков "
        "выполнения работы исполнитель уплачивает потребителю за каждый день "
        "просрочки неустойку в размере трёх процентов цены выполнения работы, "
        "но не более цены выполнения отдельного вида работы. На основании "
        "статьи 709 Гражданского кодекса РФ исполнитель обязан передать "
        "результат работы в оговорённый срок."
    ),
    "overcharge": (
        "В соответствии со статьёй 709 Гражданского кодекса РФ, если договором "
        "подряда предусмотрена твёрдая цена, подрядчик не вправе требовать её "
        "увеличения без письменного согласия заказчика. Согласно статье 16 "
        "Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей» условия "
        "договора, ущемляющие права потребителя по сравнению с правилами, "
        "установленными законом, недействительны."
    ),
}

_AUTO_REPAIR_DEMAND_SECTIONS = {
    "fix": (
        "безвозмездно устранить выявленные недостатки в выполненной работе "
        "в течение десяти дней с даты получения настоящей претензии "
        "(пункт 1 статьи 29, статья 22 Закона РФ от 07.02.1992 № 2300-1)"
    ),
    "refund": (
        "возвратить уплаченную стоимость работ в течение десяти дней с даты "
        "получения настоящей претензии (пункт 1 статьи 29, статья 22 Закона РФ "
        "от 07.02.1992 № 2300-1)"
    ),
    "reduce_price": (
        "уменьшить стоимость выполненных работ на соответствующую сумму в течение "
        "десяти дней с даты получения настоящей претензии (пункт 1 статьи 29, "
        "статья 22 Закона РФ от 07.02.1992 № 2300-1)"
    ),
}


def calculate_auto_repair(form_data: dict) -> dict:
    """Претензия в автосервис: ветки по violation_type (delay / bad_quality / overcharge)."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_overcharge_section"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    violation = str(data.get("violation_type", ""))
    service_name = str(data.get("service_name") or "").strip()
    car_model = str(data.get("car_model") or "").strip()
    car_plate = str(data.get("car_plate") or "").strip()
    service_date = str(data.get("service_date") or "").strip()

    try:
        price = Decimal(str(data.get("work_price") or "0"))
    except Exception:
        price = Decimal("0")

    # Intro
    intro = f"Я сдал(-а) автомобиль {car_model}" if car_model else "Я сдал(-а) автомобиль"
    if car_plate:
        intro += f" (г/н {car_plate})"
    if service_name:
        intro += f" в автосервис «{service_name}»"
    if service_date:
        intro += f" {service_date}"
    if price > 0:
        intro += f" для выполнения работ на сумму {_fmt(price)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    # Violation
    data["calculated_violation_section"] = _AUTO_REPAIR_VIOLATION_SECTIONS.get(
        violation,
        "Автосервис нарушил обязательства по договору возмездного оказания услуг.",
    )

    # Legal
    data["calculated_legal_section"] = _AUTO_REPAIR_LEGAL_SECTIONS.get(
        violation,
        (
            "В соответствии со статьёй 29 Закона РФ от 07.02.1992 № 2300-1 "
            "«О защите прав потребителей» потребитель вправе требовать "
            "устранения недостатков или возврата уплаченной суммы."
        ),
    )

    # Amount calc
    amount_parts = []
    total = Decimal("0")

    if violation == "delay":
        planned = _parse_date(data.get("planned_date"))
        if planned and price > 0:
            delay_days = max((date.today() - planned).days, 0)
            penalty = min(price * Decimal("0.03") * Decimal(delay_days), price)
            data["calculated_delay_days"] = str(delay_days)
            data["calculated_penalty"] = _fmt(penalty)
            data["calculated_penalty_section"] = (
                f"За {delay_days} дней просрочки выдачи автомобиля "
                f"неустойка составляет {_fmt(penalty)} руб. "
                f"(3% × {_fmt(price)} руб. × {delay_days} дней, не более стоимости работ, "
                f"ст. 28 ч. 5 ЗоЗПП)."
            )
            total += penalty
            amount_parts.append(
                f"неустойка за {delay_days} дн.: 3% × {_fmt(price)} × {delay_days} = {_fmt(penalty)} руб."
            )

    elif violation == "overcharge":
        try:
            agreed = Decimal(str(data["agreed_price"]))
            diff = max(price - agreed, Decimal("0"))
            data["calculated_overcharge_diff"] = _fmt(diff)
            data["calculated_overcharge_section"] = (
                f"Цена в договоре составляла {_fmt(agreed)} руб., "
                f"фактически выставлен счёт на {_fmt(price)} руб. "
                f"Разница {_fmt(diff)} руб. — незаконное завышение цены "
                f"(ст. 709 ГК РФ, ст. 16 ЗоЗПП)."
            )
            total += diff
            amount_parts.append(f"незаконное завышение цены: {_fmt(diff)} руб.")
        except Exception:
            pass

    elif violation == "bad_quality" and price > 0:
        total += price
        amount_parts.append(f"стоимость работ к возврату: {_fmt(price)} руб.")

    if amount_parts:
        data["calculated_amount_section"] = (
            "Расчёт суммы требования: "
            + "; ".join(amount_parts)
            + f". Итого: {_fmt(total)} руб."
        )
        data["calculated_total"] = _fmt(total)

    # Demand
    demand = str(data.get("demand") or "").strip()
    demand_text = _AUTO_REPAIR_DEMAND_SECTIONS.get(
        demand,
        f"выплатить {_fmt(total)} руб." if total > 0 else "удовлетворить настоящую претензию",
    )
    data["calculated_demand_section"] = (
        f"На основании изложенного прошу {demand_text}. "
        f"В случае неисполнения требования в добровольном порядке буду вынужден(-а) "
        f"обратиться с иском в суд. Согласно пункту 6 статьи 13 Закона РФ от 07.02.1992 "
        f"№ 2300-1 «О защите прав потребителей» при удовлетворении судом требований "
        f"потребителя с ответчика взыскивается штраф в размере пятидесяти процентов "
        f"от суммы, присуждённой потребителю, а также компенсация морального вреда."
    )

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


_DTP_OSAGO_VIOLATION_SECTIONS = {
    "delay": (
        "Страховая компания не исполнила обязанность по выплате страхового "
        "возмещения в установленный законом срок. По состоянию на дату "
        "настоящей претензии выплата не произведена либо произведена с нарушением срока."
    ),
    "underestimate": (
        "Страховая компания произвела выплату страхового возмещения в размере, "
        "не соответствующем реальной стоимости восстановительного ремонта, "
        "определённой по результатам независимой технической экспертизы."
    ),
    "refusal": (
        "Страховая компания отказала в выплате страхового возмещения. "
        "Отказ является незаконным, поскольку страховой случай наступил "
        "и все документы, предусмотренные Правилами ОСАГО, были предоставлены."
    ),
}


def calculate_dtp_osago(form_data: dict) -> dict:
    """Претензия в страховую по ОСАГО: пеня ст. 16.1 ч.21 ФЗ-40 + недоплата."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_underpayment_section"] = ""
    data["calculated_claim_amount"] = ""
    data["calculated_overdue_days"] = ""
    data["calculated_penalty"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    violation = str(data.get("violation_type", ""))
    insurance_company = str(data.get("insurance_company") or "").strip()
    incident_date = str(data.get("incident_date") or "").strip()
    incident_location = str(data.get("incident_location") or "").strip()
    car_model = str(data.get("car_model") or "").strip()
    car_plate = str(data.get("car_plate") or "").strip()
    claim_date_str = str(data.get("claim_date") or "").strip()
    policy_number = str(data.get("policy_number") or "").strip()

    # Intro
    intro_parts = []
    if incident_date and incident_location:
        intro_parts.append(f"{incident_date} по адресу: {incident_location} произошло ДТП")
    elif incident_date:
        intro_parts.append(f"{incident_date} произошло ДТП")
    if car_model:
        s = f"с участием моего транспортного средства {car_model}"
        if car_plate:
            s += f" (г/н {car_plate})"
        intro_parts.append(s)
    if policy_number:
        intro_parts.append(f"виновник ДТП застрахован по полису ОСАГО {policy_number}")
    if claim_date_str:
        intro_parts.append(
            f"Я обратился(-лась) в страховую компанию {insurance_company or ''} "
            f"с заявлением о страховом возмещении {claim_date_str}".strip()
        )
    data["calculated_intro_section"] = ". ".join(intro_parts).capitalize() + "." if intro_parts else ""

    # Violation
    data["calculated_violation_section"] = _DTP_OSAGO_VIOLATION_SECTIONS.get(
        violation,
        "Страховая компания нарушила обязательства по выплате страхового возмещения.",
    )

    # Legal
    data["calculated_legal_section"] = (
        "В соответствии с частью 21 статьи 16.1 Федерального закона от 25.04.2002 "
        "№ 40-ФЗ «Об обязательном страховании гражданской ответственности "
        "владельцев транспортных средств» при несоблюдении срока осуществления "
        "страховой выплаты страховщик за каждый день просрочки уплачивает "
        "потерпевшему неустойку (пеню) в размере одного процента от определённого "
        "в соответствии с настоящим Федеральным законом размера страхового "
        "возмещения. Согласно пункту 3 статьи 16.1 того же закона при "
        "удовлетворении судом требований потерпевшего — физического лица "
        "об осуществлении страховой выплаты суд взыскивает со страховщика "
        "штраф в размере пятидесяти процентов от разницы между совокупным "
        "размером страховой выплаты, определённой судом, и размером страховой "
        "выплаты, осуществлённой страховщиком в добровольном порядке."
    )

    try:
        damage = Decimal(str(data["damage_amount"]))
    except Exception:
        return data

    try:
        paid = Decimal(str(data.get("paid_amount") or "0"))
    except Exception:
        paid = Decimal("0")

    # Underpayment
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
    penalty = Decimal("0")
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

    # Amount section
    amount_parts = []
    if violation == "underestimate":
        underpayment_val = max(damage - paid, Decimal("0"))
        amount_parts.append(f"недоплата: {_fmt(damage)} − {_fmt(paid)} = {_fmt(underpayment_val)} руб.")
    elif violation in ("delay", "refusal"):
        amount_parts.append(f"страховое возмещение: {_fmt(claim_base)} руб.")
    if penalty > 0:
        amount_parts.append(f"пеня: {data.get('calculated_penalty', '')} руб.")
    total = claim_base + penalty
    if amount_parts:
        data["calculated_amount_section"] = (
            "Расчёт суммы требования: "
            + "; ".join(amount_parts)
            + f". Итого: {_fmt(total)} руб."
        )

    # Demand
    data["calculated_demand_section"] = (
        f"На основании изложенного прошу выплатить страховое возмещение "
        f"в размере {_fmt(claim_base)} руб."
        + (f", а также неустойку в размере {_fmt(penalty)} руб." if penalty > 0 else "")
        + " в течение десяти календарных дней с даты получения настоящей претензии. "
        "В случае неисполнения требования в добровольном порядке буду вынужден(-а) "
        "обратиться к финансовому уполномоченному в соответствии с Федеральным законом "
        "от 04.06.2018 № 123-ФЗ, а в последующем — с иском в суд."
    )

    return data


# ⚠️ Обновлять при изменении ключевой ставки ЦБ РФ (cbr.ru → «Ключевая ставка»).
# Актуальная ставка: 21% (обновлено 2026-05-24, решение ЦБ от 25.10.2024).
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


# TODO: формула «25 руб./час» — устаревшая редакция ВК РФ ст. 120.
# Действующая норма: 25% МРОТ × час просрочки, но не более 50% провозной платы.
# Не правится в пилоте миграции — это юр.фикс отдельной задачей.
_AIRLINE_VIOLATION_SECTIONS = {
    "delay": (
        "В нарушение договора воздушной перевозки рейс {flight_number} "
        "был задержан на {delay_hours} ч."
    ),
    "cancellation": (
        "Авиакомпания отменила рейс {flight_number}, в результате чего "
        "перевозка по договору не состоялась."
    ),
    "luggage": (
        "При перевозке рейсом {flight_number} авиакомпанией не было обеспечено "
        "сохранение багажа: багаж утрачен / повреждён."
    ),
    "refund_denied": (
        "После отказа от перевозки по рейсу {flight_number} "
        "авиакомпания отказала в возврате провозной платы."
    ),
}

_AIRLINE_LEGAL_SECTIONS = {
    "delay": (
        "В соответствии со статьёй 120 Воздушного кодекса РФ за просрочку "
        "доставки пассажира перевозчик уплачивает штраф в размере двадцати "
        "пяти процентов установленного федеральным законом минимального "
        "размера оплаты труда за каждый час просрочки, но не более "
        "пятидесяти процентов провозной платы. Кроме того, в силу пункта 5 "
        "статьи 28 Закона РФ от 07.02.1992 № 2300-1 «О защите прав "
        "потребителей» исполнитель уплачивает потребителю за каждый день "
        "просрочки исполнения обязательства неустойку в размере трёх "
        "процентов цены оказания услуги."
    ),
    "cancellation": (
        "В соответствии со статьями 107 и 108 Воздушного кодекса РФ при "
        "прекращении договора перевозки по инициативе перевозчика "
        "пассажир вправе требовать возврата провозной платы в полном "
        "объёме. В силу статьи 32 Закона РФ от 07.02.1992 № 2300-1 «О "
        "защите прав потребителей» при отказе от исполнения договора "
        "оказания услуги по причинам, не зависящим от потребителя, "
        "уплаченная по договору сумма подлежит возврату."
    ),
    "luggage": (
        "В соответствии со статьёй 119 Воздушного кодекса РФ за утрату, "
        "недостачу или повреждение (порчу) багажа перевозчик несёт "
        "ответственность в размере объявленной ценности, а при отсутствии "
        "объявленной ценности — в размере стоимости багажа, но не более "
        "шестисот рублей за килограмм веса багажа. В силу пункта 1 статьи "
        "29 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей» "
        "потребитель вправе требовать полного возмещения причинённого "
        "ущерба."
    ),
    "refund_denied": (
        "В соответствии со статьями 107 и 108 Воздушного кодекса РФ при "
        "отказе пассажира от перевозки уплаченная за перевозку сумма "
        "подлежит возврату с удержанием установленных правилами "
        "перевозчика сборов. В силу пункта 5 статьи 28 Закона РФ от "
        "07.02.1992 № 2300-1 «О защите прав потребителей» за каждый день "
        "просрочки возврата уплаченных сумм исполнитель уплачивает "
        "неустойку в размере трёх процентов цены оказания услуги."
    ),
}

_AIRLINE_VIOLATION_FALLBACK = (
    "Авиакомпания нарушила обязательства по договору воздушной перевозки."
)
_AIRLINE_LEGAL_FALLBACK = (
    "В соответствии со статьями 786, 793 ГК РФ перевозчик обязан возместить "
    "ущерб, причинённый ненадлежащим исполнением договора перевозки. В силу "
    "статьи 29 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей» "
    "потребитель вправе требовать полного возмещения причинённого вреда."
)


def calculate_airline(form_data: dict) -> dict:
    """Претензия авиакомпании. Pre-renders готовые секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_violation_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    violation = str(data.get("violation_type", "")).strip()
    flight_number = str(data.get("flight_number") or "").strip() or "—"
    route = str(data.get("route") or "").strip()
    flight_date = str(data.get("flight_date") or "").strip()
    airline_name = str(data.get("airline") or "").strip()

    try:
        ticket = Decimal(str(data.get("ticket_price") or "0"))
    except Exception:
        ticket = Decimal("0")
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

    intro_parts = []
    if airline_name:
        intro_parts.append(f"Между мной и {airline_name} заключён договор воздушной перевозки")
    else:
        intro_parts.append("Между мной и авиакомпанией заключён договор воздушной перевозки")
    if route:
        intro_parts.append(f"по маршруту {route}")
    if flight_number != "—":
        intro_parts.append(f"(рейс {flight_number})")
    if flight_date:
        intro_parts.append(f"с датой вылета {flight_date}")
    intro = ", ".join(intro_parts) + "."
    if ticket > 0:
        intro += f" Стоимость билета составила {_fmt(ticket)} руб."
    data["calculated_intro_section"] = intro

    viol_template = _AIRLINE_VIOLATION_SECTIONS.get(violation)
    if viol_template:
        data["calculated_violation_section"] = viol_template.format(
            flight_number=flight_number,
            delay_hours=delay_hours,
        )
    else:
        data["calculated_violation_section"] = _AIRLINE_VIOLATION_FALLBACK

    data["calculated_legal_section"] = _AIRLINE_LEGAL_SECTIONS.get(
        violation, _AIRLINE_LEGAL_FALLBACK
    )

    amount_parts = []
    total = Decimal("0")
    if violation == "delay" and delay_hours > 0 and ticket > 0:
        delay_comp = Decimal("25") * Decimal(delay_hours)
        fine = (ticket * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += delay_comp + fine
        amount_parts.append(
            f"компенсация за задержку {delay_hours} ч.: 25 × {delay_hours} = "
            f"{_fmt(delay_comp)} руб."
        )
        amount_parts.append(
            f"штраф 50% от стоимости билета (ст. 28 ч. 5 ЗоЗПП): "
            f"{_fmt(fine)} руб."
        )
        data["calculated_delay_comp"] = _fmt(delay_comp)
        data["calculated_fine"] = _fmt(fine)
    elif violation in ("cancellation", "refund_denied") and ticket > 0:
        total += ticket
        amount_parts.append(f"возврат стоимости билета: {_fmt(ticket)} руб.")

    if extra > 0:
        total += extra
        amount_parts.append(f"возмещение дополнительных расходов: {_fmt(extra)} руб.")

    if received > 0:
        total = max(total - received, Decimal("0"))
        amount_parts.append(f"уже выплачено авиакомпанией: −{_fmt(received)} руб.")

    if amount_parts:
        data["calculated_amount_section"] = (
            "Расчёт суммы требования: "
            + "; ".join(amount_parts)
            + f". Итого к выплате: {_fmt(total)} руб."
        )
        data["calculated_total"] = _fmt(total)

    demand_subject = (
        f"выплатить {_fmt(total)} руб." if total > 0 else "удовлетворить настоящую претензию"
    )
    data["calculated_demand_section"] = (
        f"На основании изложенного прошу {demand_subject} в течение тридцати "
        f"календарных дней с даты получения настоящей претензии. В случае "
        f"неисполнения требования в добровольном порядке буду вынужден(-а) "
        f"обратиться с жалобой в Федеральное агентство воздушного транспорта "
        f"(Росавиация) и с иском в суд. Согласно пункту 6 статьи 13 Закона РФ "
        f"от 07.02.1992 № 2300-1 «О защите прав потребителей» при удовлетворении "
        f"судом требований потребителя с ответчика взыскивается штраф в "
        f"размере пятидесяти процентов от суммы, присуждённой потребителю."
    )
    return data


_COURT_OBJECTION_SECTIONS = {
    "dispute_debt": (
        "Я оспариваю само существование задолженности перед взыскателем. "
        "На момент рассмотрения дела задолженности не было и не имеется."
    ),
    "dispute_amount": (
        "Я оспариваю размер взысканной суммы как неверный и завышенный. "
        "Правильный размер задолженности существенно отличается от указанного в приказе."
    ),
    "already_paid": (
        "Задолженность была погашена полностью или частично до вынесения приказа. "
        "Я располагаю документами, подтверждающими произведённые платежи взыскателю."
    ),
    "procedural": (
        "Был нарушен порядок вынесения судебного приказа, либо истёк срок исковой давности "
        "по требованию взыскателя, либо иные процессуальные основания отмены приказа."
    ),
}


def calculate_court_order(form_data: dict) -> dict:
    """Возражение на судебный приказ. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_receipt_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_objection_section", "")
    data.setdefault("calculated_additional_block", "")
    data.setdefault("calculated_demand_section", "")

    case_num = str(data.get("case_number") or "").strip() or "—"
    order_date = str(data.get("order_date") or "").strip()
    receive_date = str(data.get("receive_date") or "").strip()
    creditor = str(data.get("creditor_name") or "").strip() or "взыскатель"
    objection_reason = str(data.get("objection_reason") or "").strip()
    additional = str(data.get("additional_desc") or "").strip()

    try:
        amount = Decimal(str(data.get("debt_amount") or "0"))
    except Exception:
        amount = Decimal("0")

    intro_parts = ["Судебный приказ", f"№ {case_num}"]
    if order_date:
        intro_parts.append(f"от {order_date}")
    intro_parts.append(f"взыскатель — {creditor}")
    intro_parts.append(f"сумма взыскания — {_fmt(amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    receipt_text = (
        f"Судебный приказ получен мной {receive_date}. Настоящее возражение подаётся "
        f"в установленный десятидневный срок в соответствии со статьей 128 "
        f"Гражданского процессуального кодекса Российской Федерации."
    )
    data["calculated_receipt_section"] = receipt_text

    legal_text = (
        "В соответствии со статьёй 128 Гражданского процессуального кодекса РФ должник "
        "вправе в течение десяти дней со дня получения судебного приказа представить "
        "возражения против его исполнения. Согласно статье 129 ГПК РФ судья обязан отменить "
        "судебный приказ при поступлении возражений должника, после чего взыскатель вправе "
        "предъявить своё требование в порядке искового производства. Конституционный Суд РФ "
        "постановил, что для принятия возражения закон не требует их мотивировки — достаточно "
        "выражения несогласия с исполнением приказа."
    )
    data["calculated_legal_section"] = legal_text

    objection_template = _COURT_OBJECTION_SECTIONS.get(
        objection_reason,
        "Я выражаю несогласие с исполнением судебного приказа по основаниям, "
        "указанным в доп. описании."
    )
    data["calculated_objection_section"] = objection_template

    if additional:
        data["calculated_additional_block"] = additional

    demand_text = (
        f"На основании изложенного прошу отменить судебный приказ № {case_num} "
        f"полностью на основании статьи 129 Гражданского процессуального кодекса РФ. "
        f"К возражению прилагается: копия документа, подтверждающего дату получения "
        f"судебного приказа."
    )
    data["calculated_demand_section"] = demand_text

    return data


def calculate_rental_deposit(form_data: dict) -> dict:
    """Претензия о возврате залога. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")
    data.setdefault("calculated_wear_block", "")

    landlord = str(data.get("landlord_name") or "").strip() or "арендодателю"
    apartment = str(data.get("apartment_address") or "").strip()
    move_in = str(data.get("move_in_date") or "").strip()
    move_out = str(data.get("move_out_date") or "").strip()
    contract_num = str(data.get("contract_number") or "").strip()
    deposit_reason = str(data.get("deposit_reason") or "").strip()

    try:
        deposit = Decimal(str(data.get("deposit_amount") or "0"))
    except Exception:
        deposit = Decimal("0")

    intro_parts = []
    if apartment:
        intro_parts.append(f"Арендованная квартира: {apartment}")
    intro_parts.append(f"Период аренды: {move_in} — {move_out}")
    if contract_num:
        intro_parts.append(f"Договор аренды № {contract_num}")
    intro_parts.append(f"Размер обеспечительного платежа (залога): {_fmt(deposit)} руб.")
    data["calculated_intro_section"] = ". ".join(intro_parts) + "."

    legal_text = (
        "На основании ст. 381.1 ГК РФ обеспечительный платёж подлежит возврату, "
        "если предусмотренные договором обстоятельства не наступили или договор "
        "прекращён. В соответствии со ст. 622 ГК РФ после прекращения договора "
        "аренды все обязательства сторон, включая возврат обеспечительного платежа, "
        "прекращаются. Ст. 1102 ГК РФ обязывает лицо, без законных оснований "
        "удерживающее чужие денежные средства, их вернуть. За незаконное удержание "
        "денежных средств начисляются проценты по ключевой ставке ЦБ РФ (ст. 395 ГК РФ)."
    )
    data["calculated_legal_section"] = legal_text

    wear_block = ""
    if deposit_reason in ("damages_fake", "wear_normal"):
        wear_block = (
            "Нормальный износ квартиры в результате её использования по назначению "
            "не является ущербом, за который арендатор несёт ответственность (ст. 616, "
            "622 ГК РФ). Арендодатель обязан документально подтвердить реальный ущерб, "
            "причинённый сверх нормального износа."
        )
    data["calculated_wear_block"] = wear_block

    amount_text = (
        f"Размер требуемой к возврату суммы: {_fmt(deposit)} руб. "
        f"Срок возврата: 10 дней с даты получения настоящей претензии."
    )
    data["calculated_amount_section"] = amount_text

    demand_text = (
        f"На основании изложенного прошу вернуть обеспечительный платёж в размере "
        f"{_fmt(deposit)} руб. в течение 10 дней с даты получения настоящей претензии. "
        f"В случае неисполнения требования в добровольном порядке буду вынужден(-а) "
        f"обратиться в суд с требованием о возврате суммы залога, уплате процентов за "
        f"пользование чужими деньгами (ст. 395 ГК РФ), взыскании морального вреда и "
        f"судебных расходов."
    )
    data["calculated_demand_section"] = demand_text

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
    "rental_deposit": calculate_rental_deposit,
    "court_order": calculate_court_order,
}
