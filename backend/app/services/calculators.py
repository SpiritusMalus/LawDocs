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


_SHOP_VIOLATION_SECTIONS = {
    "defect": (
        "Приобретённый товар оказался ненадлежащего качества: "
        "в нём выявлены недостатки, которые не были оговорены продавцом при продаже."
    ),
    "return14": (
        "Продавец отказывает в возврате товара надлежащего качества "
        "в установленный законом четырнадцатидневный срок."
    ),
    "warranty": (
        "Продавец (изготовитель) уклоняется от проведения гарантийного ремонта "
        "товара либо нарушает установленные законом сроки его выполнения."
    ),
}

_SHOP_LEGAL_SECTIONS = {
    "defect": (
        "В соответствии со статьёй 18 Закона РФ от 07.02.1992 № 2300-1 «О защите "
        "прав потребителей» потребитель в случае обнаружения в товаре недостатков, "
        "если они не были оговорены продавцом, по своему выбору вправе потребовать "
        "замены на товар той же марки, соразмерного уменьшения покупной цены, "
        "незамедлительного безвозмездного устранения недостатков, возмещения "
        "расходов на их исправление, а также возврата уплаченной суммы. Согласно "
        "статье 475 Гражданского кодекса Российской Федерации покупатель вправе "
        "отказаться от исполнения договора купли-продажи и потребовать возврата "
        "уплаченной за товар суммы. Статья 23 Закона РФ от 07.02.1992 № 2300-1 "
        "устанавливает неустойку за нарушение сроков удовлетворения требований "
        "потребителя в размере одного процента цены товара за каждый день просрочки."
    ),
    "return14": (
        "В соответствии со статьёй 25 Закона РФ от 07.02.1992 № 2300-1 «О защите "
        "прав потребителей» потребитель вправе обменять непродовольственный товар "
        "надлежащего качества на аналогичный товар у продавца, у которого этот товар "
        "был приобретён, в течение четырнадцати дней, не считая дня его покупки, "
        "если указанный товар не подошёл по форме, габаритам, фасону, расцветке, "
        "размеру или комплектации. При отсутствии аналогичного товара потребитель "
        "вправе возвратить приобретённый товар продавцу и получить уплаченную "
        "за него денежную сумму."
    ),
    "warranty": (
        "В соответствии со статьёй 18 Закона РФ от 07.02.1992 № 2300-1 «О защите "
        "прав потребителей» продавец обязан принять товар ненадлежащего качества "
        "и провести гарантийный ремонт. Статья 20 того же Закона устанавливает, "
        "что недостатки должны быть устранены незамедлительно. Согласно статье 23 "
        "за нарушение срока проведения гарантийного ремонта продавец уплачивает "
        "потребителю неустойку в размере одного процента цены товара за каждый "
        "день просрочки."
    ),
}

_SHOP_DEMAND_SECTIONS = {
    "refund": "возвратить уплаченную за товар сумму",
    "replace": "заменить товар на аналогичный надлежащего качества",
    "repair": "провести гарантийный ремонт товара в установленный законом срок",
}


def calculate_shop(form_data: dict) -> dict:
    """Претензия в магазин: неустойка 1%/день по ст. 23 ЗоЗПП."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    store_name = str(data.get("store_name") or "").strip()
    product_name = str(data.get("product_name") or "").strip()
    purchase_date_str = str(data.get("purchase_date") or "").strip()
    problem_type = str(data.get("problem_type") or "").strip()
    demand = str(data.get("demand") or "").strip()

    try:
        price = Decimal(str(data.get("product_price") or "0"))
    except Exception:
        price = Decimal("0")

    # Intro
    intro = "Мной приобретён товар"
    if product_name:
        intro = f"Мной приобретён товар: {product_name}"
    if store_name:
        intro += f" в магазине «{store_name}»"
    if purchase_date_str:
        intro += f" {purchase_date_str}"
    if price > 0:
        intro += f", стоимостью {_fmt(price)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    data["calculated_violation_section"] = _SHOP_VIOLATION_SECTIONS.get(
        problem_type,
        "Продавец нарушил права потребителя при продаже товара или рассмотрении рекламации.",
    )

    data["calculated_legal_section"] = _SHOP_LEGAL_SECTIONS.get(
        problem_type, _SHOP_LEGAL_SECTIONS["defect"]
    )

    # Penalty
    start = _parse_date(data.get("penalty_start_date")) or _parse_date(data.get("appeal_date"))
    penalty = Decimal("0")
    if start and price > 0:
        delay_days = max((date.today() - start).days, 0)
        penalty = min(price * Decimal("0.01") * Decimal(delay_days), price)
        data["calculated_penalty_days"] = str(delay_days)
        data["calculated_penalty"] = _fmt(penalty)
        data["calculated_penalty_section"] = (
            f"За {delay_days} дней просрочки исполнения требования "
            f"неустойка составляет {_fmt(penalty)} руб. "
            f"(1% × {_fmt(price)} руб. × {delay_days} дней, не более стоимости товара, "
            f"статья 23 Закона РФ от 07.02.1992 № 2300-1)."
        )

    # Demand
    demand_text = _SHOP_DEMAND_SECTIONS.get(demand, "удовлетворить настоящую претензию")
    data["calculated_demand_section"] = (
        f"На основании изложенного прошу {demand_text} в течение десяти дней "
        f"с даты получения настоящей претензии (статья 22 Закона РФ от 07.02.1992 № 2300-1)."
        + (f" Прошу также выплатить неустойку в размере {_fmt(penalty)} руб." if penalty > 0 else "")
        + " В случае неисполнения требования в добровольном порядке буду вынужден(-а) обратиться "
        "с иском в суд. При удовлетворении судом требований с ответчика будет взыскан штраф "
        "в размере пятидесяти процентов от присуждённой суммы (статья 13 Закона РФ от 07.02.1992 "
        "№ 2300-1), а также компенсация морального вреда."
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


_GYM_REFUND_LEGAL_SECTIONS = {
    "club_closed": (
        "В соответствии со статьёй 451 Гражданского кодекса Российской Федерации "
        "существенное изменение обстоятельств, из которых стороны исходили при "
        "заключении договора, является основанием для его изменения или расторжения. "
        "Согласно статье 32 Закона РФ от 07.02.1992 № 2300-1 «О защите прав "
        "потребителей» при расторжении договора услугодатель обязан возвратить "
        "потребителю уплаченную сумму за вычетом фактически понесённых расходов."
    ),
    "terms_changed": (
        "В соответствии с пунктом 1 статьи 16 Закона РФ от 07.02.1992 № 2300-1 "
        "«О защите прав потребителей» условия договора, ущемляющие права "
        "потребителя по сравнению с правилами, установленными законами или иными "
        "правовыми актами Российской Федерации в области защиты прав потребителей, "
        "признаются недействительными. Согласно статье 32 того же Закона потребитель "
        "вправе отказаться от исполнения договора об оказании услуг в любое время."
    ),
    "medical": (
        "В соответствии со статьёй 32 Закона РФ от 07.02.1992 № 2300-1 «О защите "
        "прав потребителей» потребитель вправе отказаться от исполнения договора "
        "об оказании услуг в любое время при условии оплаты исполнителю фактически "
        "понесённых им расходов. Наличие медицинских противопоказаний является "
        "объективным основанием для расторжения договора."
    ),
    "voluntary": (
        "В соответствии со статьёй 32 Закона РФ от 07.02.1992 № 2300-1 «О защите "
        "прав потребителей» и статьёй 782 Гражданского кодекса Российской Федерации "
        "потребитель вправе отказаться от исполнения договора об оказании услуг в "
        "любое время при условии оплаты исполнителю фактически понесённых им расходов "
        "по исполнению обязательств по данному договору. Клуб обязан возвратить "
        "уплаченную сумму за вычетом стоимости фактически оказанных услуг."
    ),
}

_GYM_REFUND_LEGAL_DEFAULT = (
    "В соответствии со статьёй 32 Закона РФ от 07.02.1992 № 2300-1 «О защите прав "
    "потребителей» потребитель вправе отказаться от исполнения договора об оказании "
    "услуг в любое время при условии оплаты исполнителю фактически понесённых им "
    "расходов. Фитнес-клуб обязан возвратить уплаченную сумму пропорционально "
    "неиспользованному периоду."
)


def calculate_gym_refund(form_data: dict) -> dict:
    """Фитнес-клуб: возврат за неиспользованный период абонемента (ст. 32 ЗоЗПП)."""
    data = dict(form_data)
    data["calculated_refund_section"] = ""
    data["calculated_refund_amount"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    club_name = str(data.get("club_name") or "").strip()
    purchase_date_str = str(data.get("purchase_date") or "").strip()
    subscription_period = str(data.get("subscription_period") or "").strip()
    reason = str(data.get("reason") or "").strip()

    try:
        sub_price = Decimal(str(data.get("subscription_price") or "0"))
    except Exception:
        sub_price = Decimal("0")

    # Intro
    intro = f"Мной приобретён абонемент"
    if club_name:
        intro += f" в фитнес-клубе «{club_name}»"
    if purchase_date_str:
        intro += f" {purchase_date_str}"
    if subscription_period:
        intro += f", сроком {subscription_period}"
    if sub_price > 0:
        intro += f", стоимостью {_fmt(sub_price)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    reason_labels = {
        "club_closed": "Фитнес-клуб прекратил оказание услуг (закрылся или перенёс деятельность), что лишает потребителя возможности воспользоваться оплаченным абонементом.",
        "terms_changed": "Фитнес-клуб в одностороннем порядке изменил условия предоставления услуг, ухудшив положение потребителя по сравнению с условиями договора.",
        "medical": "Потребителю выявлены медицинские противопоказания к занятиям физической культурой, исключающие возможность использования абонемента.",
        "voluntary": "Потребитель принял решение об отказе от дальнейшего использования фитнес-услуг и расторжении договора в соответствии с действующим законодательством.",
    }
    data["calculated_violation_section"] = reason_labels.get(
        reason, "Потребитель требует расторжения договора и возврата денежных средств за неиспользованный период абонемента."
    )

    data["calculated_legal_section"] = _GYM_REFUND_LEGAL_SECTIONS.get(reason, _GYM_REFUND_LEGAL_DEFAULT)

    # Amount calc — приоритет: ручная сумма, потом пропорция
    refund = Decimal("0")
    try:
        user_amount = Decimal(str(data.get("refund_amount") or "0"))
        if user_amount > 0:
            refund = user_amount
            data["calculated_refund_amount"] = _fmt(refund)
            data["calculated_refund_section"] = f"Сумма к возврату за неиспользованный период: {_fmt(refund)} руб."
            data["calculated_amount_section"] = data["calculated_refund_section"]
    except Exception:
        pass

    if refund == 0:
        purchase = _parse_date(data.get("purchase_date"))
        refund_request = _parse_date(data.get("refund_request_date")) or date.today()
        total_days = _parse_subscription_days(data.get("subscription_period"))

        if purchase and total_days and total_days > 0 and sub_price > 0:
            end_date = purchase + timedelta(days=total_days)
            unused_days = max((end_date - refund_request).days, 0)
            refund = (sub_price / Decimal(total_days) * Decimal(unused_days)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            data["calculated_total_days"] = str(total_days)
            data["calculated_unused_days"] = str(unused_days)
            data["calculated_refund_amount"] = _fmt(refund)
            data["calculated_refund_section"] = (
                f"Расчёт суммы к возврату: "
                f"{_fmt(sub_price)} руб. / {total_days} дней × {unused_days} дней = "
                f"{_fmt(refund)} руб."
            )
            data["calculated_amount_section"] = data["calculated_refund_section"]

    # Demand
    if refund > 0:
        data["calculated_demand_section"] = (
            f"На основании изложенного прошу расторгнуть договор на оказание "
            f"физкультурно-оздоровительных услуг и возвратить уплаченные денежные средства "
            f"в размере {_fmt(refund)} руб. в течение десяти дней с даты получения "
            f"настоящей претензии (статья 31 Закона РФ от 07.02.1992 № 2300-1). "
            f"При нарушении срока возврата буду начислять неустойку в размере трёх "
            f"процентов от суммы задолженности за каждый день просрочки (статья 28 "
            f"часть 5 Закона РФ от 07.02.1992 № 2300-1). При отказе — обращение в суд: "
            f"штраф 50% от присуждённой суммы (статья 13 Закона), компенсация морального вреда."
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


_EMPLOYER_VIOLATION_SECTIONS = {
    "salary_delay": "Работодатель задержал выплату заработной платы сверх установленных статьёй 136 Трудового кодекса РФ сроков.",
    "underpayment": "Работодатель произвёл неполный расчёт: заработная плата выплачена в размере, не соответствующем фактически отработанному времени и условиям трудового договора.",
    "dismissal": "Работодатель произвёл незаконное увольнение без законного основания и без соблюдения установленной процедуры.",
    "vacation": "Работодатель не выплатил отпускные (компенсацию за неиспользованный отпуск) в установленные законом сроки.",
}

_EMPLOYER_LEGAL_SECTIONS = {
    "salary_delay": (
        "В соответствии со статьёй 136 Трудового кодекса Российской Федерации "
        "заработная плата выплачивается не реже чем каждые полмесяца в день, "
        "установленный правилами внутреннего трудового распорядка, коллективным "
        "договором, трудовым договором. Согласно статье 236 Трудового кодекса "
        "РФ при нарушении работодателем установленного срока выплаты заработной "
        "платы работодатель обязан выплатить их с уплатой процентов (денежной "
        "компенсации) в размере не ниже одной сто пятидесятой действующей в "
        "это время ключевой ставки Банка России от невыплаченных в срок сумм "
        "за каждый день задержки."
    ),
    "underpayment": (
        "В соответствии со статьёй 22 Трудового кодекса Российской Федерации "
        "работодатель обязан выплачивать в полном размере причитающуюся работникам "
        "заработную плату в сроки, установленные в соответствии с настоящим "
        "Кодексом, коллективным договором, правилами внутреннего трудового "
        "распорядка, трудовыми договорами. Согласно статье 236 ТК РФ при задержке "
        "выплат работодатель уплачивает проценты в размере не ниже 1/150 ключевой "
        "ставки ЦБ за каждый день просрочки."
    ),
    "vacation": (
        "В соответствии со статьёй 140 Трудового кодекса Российской Федерации "
        "при прекращении трудового договора выплата всех сумм, причитающихся "
        "работнику от работодателя, производится в день увольнения работника. "
        "Согласно статье 127 ТК РФ при увольнении работнику выплачивается "
        "денежная компенсация за все неиспользованные отпуска. Статья 236 ТК РФ "
        "устанавливает ответственность за задержку выплат: 1/150 ключевой ставки "
        "ЦБ за каждый день просрочки."
    ),
}

_EMPLOYER_LEGAL_DEFAULT = (
    "В соответствии со статьями 136, 140 и 236 Трудового кодекса Российской "
    "Федерации работодатель обязан выплачивать заработную плату в установленные "
    "сроки и несёт ответственность за задержку выплат в виде уплаты денежной "
    "компенсации в размере не ниже 1/150 действующей ключевой ставки Банка "
    "России от задержанной суммы за каждый день просрочки."
)


def calculate_employer(form_data: dict) -> dict:
    """Претензия работодателю: компенсация 1/150 × ставки ЦБ за каждый день задержки (ст. 236 ТК РФ)."""
    data = dict(form_data)
    data["calculated_compensation_section"] = ""
    data["calculated_compensation"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    violation = str(data.get("violation_type") or "").strip()
    company_name = str(data.get("company_name") or "").strip()
    position = str(data.get("position") or "").strip()
    hire_date = str(data.get("hire_date") or "").strip()
    debt_period = str(data.get("debt_period") or "").strip()

    # Intro
    intro = "Я работаю"
    if position:
        intro += f" в должности {position}"
    if company_name:
        intro += f" в организации {company_name}"
    if hire_date:
        intro += f" с {hire_date}"
    intro += "."
    if debt_period:
        intro += f" Задолженность образовалась за период: {debt_period}."
    data["calculated_intro_section"] = intro

    data["calculated_violation_section"] = _EMPLOYER_VIOLATION_SECTIONS.get(
        violation,
        "Работодатель нарушил трудовое законодательство в части выплаты денежных средств.",
    )

    data["calculated_legal_section"] = _EMPLOYER_LEGAL_SECTIONS.get(
        violation, _EMPLOYER_LEGAL_DEFAULT
    )

    last_paid = _parse_date(data.get("last_payment_date"))
    if not last_paid:
        try:
            debt = Decimal(str(data["debt_amount"]))
            data["calculated_amount_section"] = f"Сумма задолженности: {_fmt(debt)} руб."
            data["calculated_demand_section"] = (
                f"На основании изложенного прошу выплатить задолженность в размере "
                f"{_fmt(debt)} руб. в течение трёх рабочих дней с даты получения "
                f"настоящей претензии. В случае неисполнения буду вынужден(-а) "
                f"обратиться с жалобой в Государственную инспекцию труда "
                f"(онлайнинспекция.рф) и с иском в суд."
            )
        except Exception:
            pass
        return data

    delay_days = max((date.today() - last_paid).days, 0)

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

    data["calculated_amount_section"] = (
        f"Расчёт компенсации по ст. 236 ТК РФ: "
        f"{_fmt(debt)} руб. × 1/150 × {_CB_RATE}% × {delay_days} дн. = {_fmt(compensation)} руб. "
        f"Итого к выплате: {_fmt(debt)} + {_fmt(compensation)} = {_fmt(total)} руб."
    )

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу выплатить задолженность по заработной плате "
        f"в размере {_fmt(debt)} руб. и компенсацию за задержку в размере "
        f"{_fmt(compensation)} руб., итого {_fmt(total)} руб., в течение трёх рабочих "
        f"дней с даты получения настоящей претензии. В случае неисполнения буду "
        f"вынужден(-а) обратиться с жалобой в Государственную инспекцию труда "
        f"(онлайнинспекция.рф), прокуратуру, а также с иском в суд."
    )

    return data


_REPAIR_DEMAND_SECTIONS = {
    "fix": (
        "безвозмездно устранить выявленные недостатки в выполненной работе "
        "в течение десяти дней с даты получения настоящей претензии "
        "(статья 30 Закона РФ от 07.02.1992 № 2300-1)"
    ),
    "discount": (
        "соразмерно уменьшить установленную за работу цену с возвратом "
        "разницы в течение десяти дней с даты получения настоящей претензии "
        "(пункт 1 статьи 29 Закона РФ от 07.02.1992 № 2300-1)"
    ),
    "third_party": (
        "возместить расходы, понесённые мной на исправление недостатков "
        "иным подрядчиком, в течение десяти дней с даты получения настоящей претензии "
        "(пункт 1 статьи 29 Закона РФ от 07.02.1992 № 2300-1)"
    ),
    "refund": (
        "расторгнуть договор подряда и возвратить уплаченную стоимость работ "
        "в течение десяти дней с даты получения настоящей претензии "
        "(пункт 3 статьи 29 Закона РФ от 07.02.1992 № 2300-1)"
    ),
}


def calculate_repair(form_data: dict) -> dict:
    """Претензия подрядчику: неустойка 3%/день от даты обнаружения недостатков (ст. 28 ч. 5 ЗоЗПП)."""
    data = dict(form_data)
    data["calculated_penalty_section"] = ""
    data["calculated_penalty"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    contractor_name = str(data.get("contractor_name") or "").strip()
    work_type = str(data.get("work_type") or "").strip()
    contract_date = str(data.get("contract_date") or "").strip()
    contract_number = str(data.get("contract_number") or "").strip()
    work_end_date = str(data.get("work_end_date") or "").strip()
    defect_discovery_date_str = str(data.get("defect_discovery_date") or "").strip()
    demand = str(data.get("demand") or "").strip()

    try:
        price = Decimal(str(data.get("work_price") or "0"))
    except Exception:
        price = Decimal("0")

    # Intro
    intro = "Между мной и"
    if contractor_name:
        intro += f" {contractor_name}"
    if contract_number:
        intro += f" заключён договор подряда № {contract_number}"
    elif contract_date:
        intro += f" заключён договор подряда от {contract_date}"
    else:
        intro += " заключён договор подряда"
    if work_type:
        intro += f" на выполнение работ: {work_type}"
    if price > 0:
        intro += f", стоимостью {_fmt(price)} руб."
    if work_end_date:
        intro += f" Работы сданы {work_end_date}."
    intro += "."
    data["calculated_intro_section"] = intro

    data["calculated_violation_section"] = (
        f"В выполненной работе выявлены недостатки."
        + (f" Дата обнаружения: {defect_discovery_date_str}." if defect_discovery_date_str else "")
    )

    data["calculated_legal_section"] = (
        "В соответствии с пунктом 1 статьи 29 Закона РФ от 07.02.1992 № 2300-1 "
        "«О защите прав потребителей» при обнаружении недостатков выполненной работы "
        "потребитель вправе по своему выбору потребовать: безвозмездного устранения "
        "недостатков выполненной работы; соответствующего уменьшения цены выполненной "
        "работы; возмещения понесённых им расходов по устранению недостатков "
        "выполненной работы своими силами или с помощью третьих лиц. На основании "
        "статьи 723 Гражданского кодекса Российской Федерации подрядчик несёт "
        "ответственность за ненадлежащее качество выполненных работ. Согласно "
        "пункту 5 статьи 28 Закона РФ от 07.02.1992 № 2300-1 за каждый день "
        "просрочки устранения недостатков исполнитель уплачивает неустойку "
        "в размере трёх процентов цены выполнения работы."
    )

    # Penalty
    discovery = _parse_date(data.get("defect_discovery_date"))
    penalty = Decimal("0")
    if discovery and price > 0:
        delay_days = max((date.today() - discovery).days, 0)
        penalty = min(price * Decimal("0.03") * Decimal(delay_days), price)
        data["calculated_penalty_days"] = str(delay_days)
        data["calculated_penalty"] = _fmt(penalty)
        data["calculated_penalty_section"] = (
            f"За {delay_days} дней с момента обнаружения недостатков "
            f"неустойка составляет {_fmt(penalty)} руб. "
            f"(3% × {_fmt(price)} руб. × {delay_days} дней, не более стоимости работ, "
            f"ст. 28 ч. 5 ЗоЗПП)."
        )
        data["calculated_amount_section"] = data["calculated_penalty_section"]

    # Demand
    demand_text = _REPAIR_DEMAND_SECTIONS.get(
        demand,
        f"устранить выявленные недостатки в течение десяти дней с даты получения настоящей претензии",
    )
    demand_section = f"На основании изложенного прошу {demand_text}."
    if penalty > 0:
        demand_section += f" Прошу также выплатить неустойку в размере {_fmt(penalty)} руб."
    demand_section += (
        " В случае неисполнения требования в добровольном порядке буду вынужден(-а) "
        "обратиться с иском в суд. При удовлетворении судом требований с ответчика "
        "будет взыскан штраф в размере пятидесяти процентов от присуждённой суммы "
        "(статья 13 Закона РФ от 07.02.1992 № 2300-1), а также компенсация морального вреда."
    )
    data["calculated_demand_section"] = demand_section

    return data


_INSURANCE_LEGAL_SECTIONS = {
    "osago": (
        "В соответствии со статьёй 12 Федерального закона от 25.04.2002 № 40-ФЗ "
        "«Об обязательном страховании гражданской ответственности владельцев "
        "транспортных средств» страховщик обязан произвести страховую выплату "
        "в течение двадцати календарных дней со дня принятия к рассмотрению "
        "заявления потерпевшего. Согласно части 21 статьи 16.1 того же Федерального "
        "закона при несоблюдении срока страховой выплаты страховщик уплачивает "
        "неустойку в размере одного процента от суммы страхового возмещения за каждый "
        "день просрочки. Согласно пункту 3 статьи 16.1 при удовлетворении судом "
        "требований потерпевшего со страховщика взыскивается штраф в размере "
        "пятидесяти процентов от разницы между совокупным размером страховой "
        "выплаты, определённой судом, и размером, осуществлённым добровольно."
    ),
    "kasko": (
        "В соответствии со статьёй 929 Гражданского кодекса Российской Федерации "
        "по договору имущественного страхования страховщик обязуется при наступлении "
        "страхового случая возместить страхователю или выгодоприобретателю убытки "
        "в пределах определённой договором страховой суммы. Согласно статье 943 ГК РФ "
        "условия, на которых заключается договор страхования, могут быть определены "
        "в стандартных правилах страхования. В силу пункта 5 статьи 28 Закона РФ "
        "от 07.02.1992 № 2300-1 «О защите прав потребителей» при нарушении сроков "
        "исполнения обязательства исполнитель уплачивает неустойку в размере трёх "
        "процентов цены услуги за каждый день просрочки."
    ),
    "other": (
        "В соответствии со статьёй 929 Гражданского кодекса Российской Федерации "
        "страховщик обязан при наступлении страхового случая выплатить страховое "
        "возмещение в размере, предусмотренном договором страхования. Согласно "
        "статье 4 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей» "
        "страховщик обязан оказывать услуги надлежащего качества. Статья 29 того "
        "же Закона предоставляет потребителю право требовать возмещения причинённых "
        "убытков в полном объёме."
    ),
}

_INSURANCE_VIOLATION_SECTIONS = {
    "underestimate": (
        "Страховая компания произвела выплату в размере, не соответствующем "
        "реальному ущербу: выплаченная сумма занижена по сравнению с оценкой "
        "независимой технической экспертизы."
    ),
    "refusal": (
        "Страховая компания отказала в осуществлении страховой выплаты. "
        "Отказ является незаконным: страховой случай наступил, все предусмотренные "
        "законом и правилами страхования документы были предоставлены страховщику."
    ),
    "delay": (
        "Страховая компания нарушила установленный законом срок осуществления "
        "страховой выплаты: по состоянию на дату настоящей претензии выплата "
        "не произведена либо произведена с нарушением срока."
    ),
}


def calculate_insurance(form_data: dict) -> dict:
    """Претензия в страховую: недоплата + пеня 1%/день (ОСАГО ст. 16.1 ФЗ-40 / КАСКО ЗоЗПП ст. 28)."""
    data = dict(form_data)
    data["calculated_underpayment_section"] = ""
    data["calculated_penalty_section"] = ""
    data["calculated_underpayment"] = ""
    data["calculated_total"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_demand_section"] = ""

    policy_type = str(data.get("policy_type") or "").strip()
    incident_type = str(data.get("incident_type") or "").strip()
    insurance_company = str(data.get("insurance_company") or "").strip()
    policy_number = str(data.get("policy_number") or "").strip()
    incident_date = str(data.get("incident_date") or "").strip()

    # Intro
    intro_parts = []
    if policy_number and incident_date:
        intro_parts.append(f"По полису № {policy_number} {incident_date} наступил страховой случай")
    elif incident_date:
        intro_parts.append(f"{incident_date} наступил страховой случай")
    if insurance_company:
        intro_parts.append(f"Я обратился(-лась) в страховую компанию {insurance_company} с заявлением о выплате страхового возмещения")
    data["calculated_intro_section"] = ". ".join(intro_parts).capitalize() + "." if intro_parts else ""

    data["calculated_violation_section"] = _INSURANCE_VIOLATION_SECTIONS.get(
        incident_type,
        "Страховая компания нарушила обязательства по договору страхования.",
    )

    data["calculated_legal_section"] = _INSURANCE_LEGAL_SECTIONS.get(
        policy_type, _INSURANCE_LEGAL_SECTIONS["other"]
    )

    try:
        actual = Decimal(str(data["actual_damage"]))
    except Exception:
        data["calculated_demand_section"] = (
            "На основании изложенного прошу произвести страховую выплату в полном "
            "объёме, определённом по результатам независимой экспертизы, в течение "
            "десяти рабочих дней с даты получения настоящей претензии. При отказе — "
            "обращение с жалобой в Банк России и Российский союз автостраховщиков, "
            "а также с иском в суд."
        )
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

    penalty = Decimal("0")
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

    claim_total = underpayment + penalty
    data["calculated_demand_section"] = (
        f"На основании изложенного прошу выплатить страховое возмещение "
        f"в размере {_fmt(underpayment)} руб."
        + (f", а также неустойку в размере {_fmt(penalty)} руб." if penalty > 0 else "")
        + f", итого {_fmt(claim_total)} руб., в течение десяти рабочих дней с даты "
        f"получения настоящей претензии. При отказе — обращение с жалобой в "
        f"Банк России и Российский союз автостраховщиков, а также с иском в суд. "
        f"При удовлетворении судом требований с ответчика будет взыскан штраф "
        f"в размере пятидесяти процентов от присуждённой суммы, а также "
        f"компенсация морального вреда и судебные расходы."
    )

    return data


_TELECOM_VIOLATION_SECTIONS = {
    "no_service": (
        "Оператор связи не оказывает услугу, предусмотренную договором: "
        "услуга полностью недоступна с даты, указанной в настоящей претензии."
    ),
    "slow_speed": (
        "Оператор связи оказывает услугу ненадлежащего качества: "
        "фактическая скорость интернет-соединения систематически не соответствует "
        "заявленной по договору."
    ),
    "illegal_charges": (
        "Оператор связи произвёл несанкционированные списания денежных средств: "
        "с лицевого счёта абонента списаны суммы за услуги, не предусмотренные "
        "заключённым договором и не подключённые по инициативе абонента."
    ),
    "disconnected": (
        "Оператор связи произвёл отключение услуг без законного основания "
        "и без надлежащего уведомления абонента в установленном порядке."
    ),
}

_TELECOM_LEGAL_SECTIONS = {
    "no_service": (
        "В соответствии со статьёй 44 Федерального закона от 07.07.2003 № 126-ФЗ "
        "«О связи» оператор связи обязан оказывать услуги связи в соответствии "
        "с законодательством Российской Федерации, национальными стандартами, "
        "техническими нормами и правилами, лицензией, а также договором об оказании "
        "услуг связи. Согласно пункту 1 статьи 4 и статье 29 Закона РФ от 07.02.1992 "
        "№ 2300-1 «О защите прав потребителей» при оказании услуги ненадлежащего "
        "качества потребитель вправе потребовать соразмерного уменьшения цены, "
        "устранения недостатков или возврата уплаченных средств."
    ),
    "slow_speed": (
        "В соответствии со статьёй 44 Федерального закона от 07.07.2003 № 126-ФЗ "
        "«О связи» оператор обязан соблюдать технические нормы качества услуг. "
        "Согласно статье 29 Закона РФ от 07.02.1992 № 2300-1 «О защите прав "
        "потребителей» при оказании услуги ненадлежащего качества потребитель "
        "вправе потребовать соразмерного уменьшения цены либо возврата уплаченных средств."
    ),
    "illegal_charges": (
        "В соответствии со статьёй 54 Федерального закона от 07.07.2003 № 126-ФЗ "
        "«О связи» оператор связи не вправе взимать с абонента плату за услуги, "
        "не предусмотренные договором об оказании услуг связи. Согласно статье 16 "
        "Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей» условия "
        "договора, ущемляющие права потребителя, недействительны. Суммы, "
        "взысканные с нарушением закона, подлежат возврату."
    ),
    "disconnected": (
        "В соответствии со статьёй 44 Федерального закона от 07.07.2003 № 126-ФЗ "
        "«О связи» оператор обязан оказывать услуги в соответствии с договором. "
        "Одностороннее прекращение оказания услуг без законного основания нарушает "
        "статью 29 Закона РФ от 07.02.1992 № 2300-1 «О защите прав потребителей», "
        "предоставляющую потребителю право требовать устранения нарушений и "
        "возмещения убытков."
    ),
}

_TELECOM_DEMAND_SECTIONS = {
    "fix": "устранить неисправность и восстановить оказание услуги связи надлежащего качества",
    "refund": "произвести перерасчёт и возвратить денежные средства за период отсутствия услуги",
    "cancel_charges": "отменить незаконно начисленные платежи и возвратить списанные суммы",
    "terminate": "расторгнуть договор об оказании услуг связи без применения штрафных санкций и возвратить остаток средств на лицевом счёте",
}


def calculate_telecom(form_data: dict) -> dict:
    """Претензия провайдеру: возврат пропорционально периоду отсутствия услуги (monthly_fee / 30 × дней)."""
    data = dict(form_data)
    data["calculated_refund_section"] = ""
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_legal_section"] = ""
    data["calculated_demand_section"] = ""

    provider_name = str(data.get("provider_name") or "").strip()
    contract_number = str(data.get("contract_number") or "").strip()
    service_type = str(data.get("service_type") or "").strip()
    problem_type = str(data.get("problem_type") or "").strip()
    problem_start_date_str = str(data.get("problem_start_date") or "").strip()
    demand = str(data.get("demand") or "").strip()

    service_labels = {
        "internet": "домашнего интернета",
        "mobile": "мобильной связи",
        "tv": "кабельного/спутникового телевидения",
        "bundle": "пакета услуг связи",
    }

    # Intro
    intro = "Между мной и"
    if provider_name:
        intro += f" {provider_name}"
    service_label = service_labels.get(service_type, "услуг связи")
    if contract_number:
        intro += f" заключён договор об оказании {service_label} № {contract_number}"
    else:
        intro += f" заключён договор об оказании {service_label}"
    if problem_start_date_str:
        intro += f". С {problem_start_date_str} оператор нарушает условия договора"
    intro += "."
    data["calculated_intro_section"] = intro

    data["calculated_violation_section"] = _TELECOM_VIOLATION_SECTIONS.get(
        problem_type,
        "Оператор связи нарушил обязательства по договору об оказании услуг связи.",
    )

    data["calculated_legal_section"] = _TELECOM_LEGAL_SECTIONS.get(
        problem_type, _TELECOM_LEGAL_SECTIONS["no_service"]
    )

    # Refund calc (только для no_service / slow_speed)
    refund = Decimal("0")
    if problem_type in ("no_service", "slow_speed"):
        start = _parse_date(data.get("problem_start_date"))
        if start:
            days = max((date.today() - start).days, 0)
            try:
                monthly = Decimal(str(data.get("monthly_fee") or "0"))
                if monthly > 0:
                    refund = (monthly / Decimal("30") * Decimal(days)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    data["calculated_refund_days"] = str(days)
                    data["calculated_refund"] = _fmt(refund)
                    data["calculated_refund_section"] = (
                        f"За {days} дней отсутствия / ненадлежащего оказания услуги "
                        f"сумма к возврату: {_fmt(monthly)} руб. / 30 × {days} дней = "
                        f"{_fmt(refund)} руб."
                    )
            except Exception:
                pass

    # Demand
    demand_text = _TELECOM_DEMAND_SECTIONS.get(demand, "устранить нарушения условий договора об оказании услуг связи")
    demand_section = (
        f"На основании изложенного прошу {demand_text} в течение десяти дней "
        f"с даты получения настоящей претензии."
    )
    if refund > 0 and demand in ("refund", "cancel_charges"):
        demand_section += f" Сумма к возврату: {_fmt(refund)} руб."
    demand_section += (
        " В случае неисполнения требования буду вынужден(-а) обратиться "
        "с жалобой в Роскомнадзор, а также с иском в суд. При удовлетворении "
        "судом требований с ответчика будет взыскан штраф в размере пятидесяти "
        "процентов от присуждённой суммы (статья 13 Закона РФ от 07.02.1992 № 2300-1)."
    )
    data["calculated_demand_section"] = demand_section

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
