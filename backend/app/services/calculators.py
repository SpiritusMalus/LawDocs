"""
Pre-LLM calculators for situations that require deterministic math.

Each calculator receives form_data and returns a new dict with injected
`calculated_*` fields that the system_prompt can reference directly.
"""

import logging
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings

logger = logging.getLogger(__name__)


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
    """Денежная сумма: разделитель тысяч (неразрывный пробел), копейки только если они есть.

    39990 → «39 990», 1234.50 → «1 234,50». Разделитель — U+00A0, чтобы число
    не разрывалось переносом строки в PDF.
    """
    q = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole = int(q)
    kopecks = int((q - whole) * 100)
    int_str = f"{whole:,}".replace(",", " ")
    if kopecks:
        return f"{int_str},{kopecks:02d}"
    return int_str


def _fmt_date_ru(d: date) -> str:
    return f"{d.day} {_MONTHS_GENITIVE[d.month - 1]} {d.year} года"


def _ru_date(value: str | None) -> str:
    """ISO-строку даты → «15 января 2024 года». Невалидное значение возвращает как есть."""
    raw = str(value or "").strip()
    d = _parse_date(raw)
    return _fmt_date_ru(d) if d else raw


def _sentence_case(s: str) -> str:
    """Заглавная только первая буква; остальные регистры сохраняются (не ломает «г. Москва»)."""
    return s[0].upper() + s[1:] if s else s


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
    contract_date = _ru_date(data.get("contract_date"))
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
    except Exception as e:
        logger.error("calculate_ddu_delay: failed to compute neustoyka: %s", e)
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
        + " В случае неисполнения требования в добровольном порядке оставляю за собой право "
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
    except Exception as e:
        logger.error("calculate_ddu_termination: failed to compute interest: %s", e)
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
        + " В случае неисполнения требования в добровольном порядке оставляю за собой право обратиться "
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
    service_date = _ru_date(data.get("service_date"))

    try:
        price = Decimal(str(data.get("work_price") or "0"))
    except Exception:
        price = Decimal("0")

    # Intro
    intro = f"Мной передан автомобиль {car_model}" if car_model else "Мной передан автомобиль"
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
        except Exception as e:
            logger.warning("calculate_auto_repair: failed to compute overcharge diff: %s", e)

    elif violation == "bad_quality":
        if price > 0:
            total += price
            amount_parts.append(f"стоимость работ к возврату: {_fmt(price)} руб.")
        else:
            logger.warning("calculate_auto_repair: bad_quality but work_price=0, demand will use generic fallback")

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
        f"В случае неисполнения требования в добровольном порядке оставляю за собой право "
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
    except Exception as e:
        logger.warning("calculate_gym_refund: failed to compute user-specified refund: %s", e)

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
    incident_date = _ru_date(data.get("incident_date"))
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
    data["calculated_intro_section"] = _sentence_case(". ".join(intro_parts)) + "." if intro_parts else ""

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
    except Exception as e:
        logger.error("calculate_dtp_osago: failed to parse damage_amount: %s", e)
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
        "В случае неисполнения требования в добровольном порядке оставляю за собой право "
        "обратиться к финансовому уполномоченному в соответствии с Федеральным законом "
        "от 04.06.2018 № 123-ФЗ, а в последующем — с иском в суд."
    )

    return data


def _get_cb_rate() -> Decimal:
    return Decimal(str(settings.CB_RATE_PERCENT))


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
    hire_date = _ru_date(data.get("hire_date"))
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
                f"настоящей претензии. В случае неисполнения оставляю за собой право "
                f"обратиться с жалобой в Государственную инспекцию труда "
                f"(онлайнинспекция.рф) и с иском в суд."
            )
        except Exception as e:
            logger.warning("calculate_employer: failed to build demand_section for unpaid debt: %s", e)
        return data

    delay_days = max((date.today() - last_paid).days, 0)

    try:
        debt = Decimal(str(data["debt_amount"]))
        compensation = debt * Decimal("1") / Decimal("150") * _get_cb_rate() / Decimal("100") * Decimal(delay_days)
        compensation = compensation.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as e:
        logger.error("calculate_employer: failed to compute compensation: %s", e)
        return data

    data["calculated_delay_days"] = str(delay_days)
    data["calculated_compensation"] = _fmt(compensation)
    total = debt + compensation
    data["calculated_compensation_section"] = (
        f"Компенсация за задержку {delay_days} дней: "
        f"{_fmt(debt)} руб. × 1/150 × {_get_cb_rate()}% × {delay_days} дней = "
        f"{_fmt(compensation)} руб. (ст. 236 ТК РФ). "
        f"Итого к выплате: {_fmt(debt)} + {_fmt(compensation)} = {_fmt(total)} руб."
    )

    data["calculated_amount_section"] = (
        f"Расчёт компенсации по ст. 236 ТК РФ: "
        f"{_fmt(debt)} руб. × 1/150 × {_get_cb_rate()}% × {delay_days} дн. = {_fmt(compensation)} руб. "
        f"Итого к выплате: {_fmt(debt)} + {_fmt(compensation)} = {_fmt(total)} руб."
    )

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу выплатить задолженность по заработной плате "
        f"в размере {_fmt(debt)} руб. и компенсацию за задержку в размере "
        f"{_fmt(compensation)} руб., итого {_fmt(total)} руб., в течение трёх рабочих "
        f"дней с даты получения настоящей претензии. В случае неисполнения "
        f"оставляю за собой право обратиться с жалобой в Государственную инспекцию труда "
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
    contract_date = _ru_date(data.get("contract_date"))
    contract_number = str(data.get("contract_number") or "").strip()
    work_end_date = _ru_date(data.get("work_end_date"))
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
        " В случае неисполнения требования в добровольном порядке оставляю за собой право "
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
    incident_date = _ru_date(data.get("incident_date"))

    # Intro
    intro_parts = []
    if policy_number and incident_date:
        intro_parts.append(f"По полису № {policy_number} {incident_date} наступил страховой случай")
    elif incident_date:
        intro_parts.append(f"{incident_date} наступил страховой случай")
    if insurance_company:
        intro_parts.append(f"Я обратился(-лась) в страховую компанию {insurance_company} с заявлением о выплате страхового возмещения")
    data["calculated_intro_section"] = _sentence_case(". ".join(intro_parts)) + "." if intro_parts else ""

    data["calculated_violation_section"] = _INSURANCE_VIOLATION_SECTIONS.get(
        incident_type,
        "Страховая компания нарушила обязательства по договору страхования.",
    )

    data["calculated_legal_section"] = _INSURANCE_LEGAL_SECTIONS.get(
        policy_type, _INSURANCE_LEGAL_SECTIONS["other"]
    )

    try:
        actual = Decimal(str(data["actual_damage"]))
    except Exception as e:
        logger.error("calculate_insurance: failed to parse actual_damage: %s", e)
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
            except Exception as e:
                logger.warning("calculate_telecom: failed to compute refund: %s", e)

    # Demand
    demand_text = _TELECOM_DEMAND_SECTIONS.get(demand, "устранить нарушения условий договора об оказании услуг связи")
    demand_section = (
        f"На основании изложенного прошу {demand_text} в течение десяти дней "
        f"с даты получения настоящей претензии."
    )
    if refund > 0 and demand in ("refund", "cancel_charges"):
        demand_section += f" Сумма к возврату: {_fmt(refund)} руб."
    demand_section += (
        " В случае неисполнения требования оставляю за собой право обратиться "
        "с жалобой в Роскомнадзор, а также с иском в суд. При удовлетворении "
        "судом требований с ответчика будет взыскан штраф в размере пятидесяти "
        "процентов от присуждённой суммы (статья 13 Закона РФ от 07.02.1992 № 2300-1)."
    )
    data["calculated_demand_section"] = demand_section

    return data


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
    flight_date = _ru_date(data.get("flight_date"))
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
        mrot = Decimal(settings.MROT)
        per_hour = (mrot * Decimal("0.25")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delay_comp_raw = per_hour * Decimal(delay_hours)
        cap = (ticket * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delay_comp = min(delay_comp_raw, cap).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        fine = cap
        total += delay_comp + fine
        amount_parts.append(
            f"компенсация за задержку {delay_hours} ч. (25% МРОТ × часы, "
            f"не более 50% провозной платы): {_fmt(delay_comp)} руб."
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
        f"неисполнения требования в добровольном порядке оставляю за собой право "
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

    case_num = str(data.get("case_number") or "").strip()
    order_date = _ru_date(data.get("order_date"))
    receive_date = _ru_date(data.get("receive_date"))
    creditor = str(data.get("creditor_name") or "").strip() or "взыскатель"
    objection_reason = str(data.get("objection_reason") or "").strip()
    additional = str(data.get("additional_desc") or "").strip()

    try:
        amount = Decimal(str(data.get("debt_amount") or "0"))
    except Exception:
        amount = Decimal("0")

    intro_parts = ["Судебный приказ"]
    if case_num:
        intro_parts.append(f"№ {case_num}")
    if order_date:
        intro_parts.append(f"от {order_date}")
    intro_parts.append(f"взыскатель — {creditor}")
    if amount > 0:
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

    order_ref = f" № {case_num}" if case_num else ""
    demand_text = (
        f"На основании изложенного прошу отменить судебный приказ{order_ref} "
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
        f"В случае неисполнения требования в добровольном порядке оставляю за собой право "
        f"обратиться в суд с требованием о возврате суммы залога, уплате процентов за "
        f"пользование чужими деньгами (ст. 395 ГК РФ), взыскании морального вреда и "
        f"судебных расходов."
    )
    data["calculated_demand_section"] = demand_text

    return data


def calculate_medical(form_data: dict) -> dict:
    """Претензия медицинской организации. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    clinic = str(data.get("clinic_name") or "").strip() or "медицинской организации"
    treatment_date_raw = str(data.get("treatment_date") or "").strip()
    problem_type = str(data.get("problem_type") or "").strip()
    demand = str(data.get("demand") or "").strip()
    insurance_type = str(data.get("insurance_type") or "").strip()

    treatment_d = _parse_date(treatment_date_raw)
    treatment_str = _fmt_date_ru(treatment_d) if treatment_d else treatment_date_raw

    try:
        paid_amount = Decimal(str(data.get("paid_amount") or "0"))
    except Exception:
        paid_amount = Decimal("0")

    insurance_note = ""
    if insurance_type == "oms":
        insurance_note = " в рамках обязательного медицинского страхования (ОМС)"
    elif insurance_type == "paid":
        insurance_note = " на платной основе"

    intro_parts = [f"Медицинская организация: {clinic}"]
    if treatment_str:
        intro_parts.append(f"дата обращения: {treatment_str}{insurance_note}")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    _LEGAL_BY_TYPE = {
        "refused": (
            "На основании ст. 19 Федерального закона от 21.11.2011 № 323-ФЗ «Об основах охраны здоровья граждан в "
            "Российской Федерации» каждый имеет право на медицинскую помощь. Согласно ст. 83 ФЗ-323 медицинская помощь "
            "в рамках программы государственных гарантий оказывается бесплатно. "
            "В соответствии со ст. 4 Закона РФ «О защите прав потребителей» исполнитель обязан оказать услугу, "
            "качество которой соответствует договору."
        ),
        "bad_treatment": (
            "В соответствии с ч. 2 ст. 19 и ст. 98 Федерального закона от 21.11.2011 № 323-ФЗ медицинские организации "
            "несут ответственность за причинение вреда жизни и (или) здоровью при оказании гражданам медицинской помощи. "
            "Согласно ст. 1068 ГК РФ юридическое лицо возмещает вред, причинённый его работником при исполнении "
            "трудовых обязанностей. "
            "На основании ст. 29 ЗоЗПП потребитель вправе требовать устранения недостатков оказанной услуги."
        ),
        "paid_forced": (
            "Согласно ст. 80 Федерального закона от 21.11.2011 № 323-ФЗ медицинская помощь в рамках программы "
            "государственных гарантий оказывается бесплатно. "
            "В соответствии со ст. 84 ФЗ-323 платные медицинские услуги оказываются исключительно при наличии "
            "добровольного письменного согласия пациента. "
            "На основании ст. 16 ЗоЗПП условия, ущемляющие права потребителя, ничтожны."
        ),
        "confidentiality": (
            "В соответствии со ст. 13 Федерального закона от 21.11.2011 № 323-ФЗ сведения о факте обращения "
            "гражданина за медицинской помощью, состоянии его здоровья и диагнозе составляют врачебную тайну. "
            "Согласно ст. 7 Федерального закона от 27.07.2006 № 152-ФЗ «О персональных данных» операторы обязаны "
            "обеспечить конфиденциальность персональных данных."
        ),
    }
    data["calculated_legal_section"] = _LEGAL_BY_TYPE.get(
        problem_type,
        "На основании ст. 19 Федерального закона от 21.11.2011 № 323-ФЗ каждый имеет право на медицинскую помощь "
        "надлежащего качества. В соответствии со ст. 4 ЗоЗПП исполнитель обязан оказать услугу надлежащего качества.",
    )

    if paid_amount > 0 and demand in ("refund", "compensation"):
        data["calculated_amount_section"] = (
            f"Сумма незаконно взысканных средств: {_fmt(paid_amount)} руб."
        )
    else:
        data["calculated_amount_section"] = ""

    _DEMAND_TEXTS = {
        "refund": (
            f"На основании изложенного прошу вернуть {_fmt(paid_amount)} руб., "
            f"незаконно взысканных за оказанные медицинские услуги, в течение 10 дней с даты получения настоящей претензии."
        ),
        "compensation": (
            "На основании изложенного прошу возместить расходы на лечение последствий "
            "в течение 10 дней с даты получения настоящей претензии."
        ),
        "redo": (
            "На основании изложенного прошу провести повторное лечение / исправить допущенные недостатки "
            "за счёт организации в разумный срок."
        ),
        "apology_and_check": (
            "На основании изложенного прошу провести внутреннюю проверку по факту допущенных нарушений "
            "и привлечь виновных к дисциплинарной ответственности."
        ),
    }
    demand_text = _DEMAND_TEXTS.get(
        demand,
        "На основании изложенного прошу устранить допущенные нарушения в течение 10 дней с даты получения настоящей претензии.",
    )
    data["calculated_demand_section"] = (
        demand_text + " "
        "В случае неисполнения требования оставляю за собой право обратиться с жалобой в Росздравнадзор (roszdravnadzor.gov.ru)"
        + (", ТФОМС" if insurance_type == "oms" else "")
        + ", прокуратуру, а также с иском в суд о компенсации морального вреда (ст. 151 ГК РФ)."
    )

    return data


def calculate_marketplace(form_data: dict) -> dict:
    """Претензия маркетплейсу. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    platform_val = str(data.get("platform") or "").strip()
    platform_other = str(data.get("platform_other") or "").strip()
    platform_name = platform_other if platform_val == "other" and platform_other else platform_val.capitalize()
    product = str(data.get("product_name") or "").strip()
    order_number = str(data.get("order_number") or "").strip()
    order_date_raw = str(data.get("order_date") or "").strip()
    problem_type = str(data.get("problem_type") or "").strip()
    demand = str(data.get("demand") or "").strip()

    order_d = _parse_date(order_date_raw)
    order_str = _fmt_date_ru(order_d) if order_d else order_date_raw

    try:
        order_amount = Decimal(str(data.get("order_amount") or "0"))
    except Exception:
        order_amount = Decimal("0")
    try:
        withheld_amount = Decimal(str(data.get("withheld_amount") or "0"))
    except Exception:
        withheld_amount = Decimal("0")

    claim_amount = withheld_amount if withheld_amount > 0 else order_amount

    intro_parts = [f"Маркетплейс: {platform_name}"]
    if product:
        intro_parts.append(f"товар: «{product}»")
    if order_number:
        intro_parts.append(f"заказ № {order_number}")
    if order_str:
        intro_parts.append(f"дата заказа: {order_str}")
    intro_parts.append(f"сумма заказа: {_fmt(order_amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    data["calculated_legal_section"] = (
        "В соответствии со ст. 26.1 Закона РФ «О защите прав потребителей» при дистанционном способе продажи товара "
        "продавец обязан передать потребителю товар, качество которого соответствует договору. "
        "Согласно Постановлению Правительства РФ от 31.12.2020 № 2463 (Правила дистанционной торговли) продавец несёт "
        "ответственность за сохранность товара до момента его передачи потребителю. "
        "На основании ст. 18 ЗоЗПП потребитель вправе потребовать возврата уплаченной суммы при продаже товара "
        "ненадлежащего качества."
        + (
            " В соответствии с ФЗ от 31.07.2025 № 289-ФЗ «Об отдельных вопросах регулирования платформенной экономики» "
            "оператор платформы несёт ответственность перед потребителем за товар, реализованный через её инфраструктуру "
            "(ст. 11), и не вправе взимать с потребителя вознаграждение, не предусмотренное договором (ст. 10)."
            if problem_type in ("penalty", "paid_return") else ""
        )
    )

    if withheld_amount > 0:
        data["calculated_amount_section"] = f"Спорная (удержанная) сумма: {_fmt(withheld_amount)} руб."
    else:
        data["calculated_amount_section"] = f"Сумма к возврату: {_fmt(order_amount)} руб."

    _DEMAND_TEXTS = {
        "return_money": f"вернуть удержанную сумму в размере {_fmt(claim_amount)} руб.",
        "refund_order": f"вернуть денежные средства за заказ в размере {_fmt(order_amount)} руб.",
        "cancel_penalty": f"отменить незаконно начисленный штраф и вернуть {_fmt(claim_amount)} руб.",
    }
    demand_text = _DEMAND_TEXTS.get(demand, f"устранить нарушение и вернуть {_fmt(claim_amount)} руб.")

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу {demand_text} в течение 10 дней с даты получения настоящей претензии. "
        f"В случае отказа оставляю за собой право обратиться с жалобой в Роспотребнадзор и с иском в суд; "
        f"штраф 50% от присуждённой суммы (ст. 13 ЗоЗПП), компенсация морального вреда, судебные расходы."
    )

    return data


def calculate_carsharing(form_data: dict) -> dict:
    """Претензия каршеринговой компании. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    company = str(data.get("company_name") or "").strip() or "каршеринговой компании"
    trip_date_raw = str(data.get("trip_date") or "").strip()
    trip_location = str(data.get("trip_location") or "").strip()
    car_plate = str(data.get("car_plate") or "").strip()
    order_id = str(data.get("order_id") or "").strip()
    violation_type = str(data.get("violation_type") or "").strip()
    has_photo = str(data.get("has_photo") or "").strip()

    trip_d = _parse_date(trip_date_raw)
    trip_str = _fmt_date_ru(trip_d) if trip_d else trip_date_raw

    try:
        claimed_amount = Decimal(str(data.get("claimed_amount") or "0"))
    except Exception:
        claimed_amount = Decimal("0")

    intro_parts = [f"Каршеринговая компания: {company}"]
    if trip_str:
        intro_parts.append(f"дата поездки: {trip_str}")
    if trip_location:
        intro_parts.append(f"место начала: {trip_location}")
    if car_plate:
        intro_parts.append(f"гос. номер: {car_plate}")
    if order_id:
        intro_parts.append(f"заказ: {order_id}")
    intro_parts.append(f"требуемая сумма: {_fmt(claimed_amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    _VIOLATION_LEGAL = {
        "preexisting_damage": (
            "Согласно ст. 620 ГК РФ арендодатель несёт ответственность за недостатки имущества, существовавшие "
            "до передачи его арендатору. На основании ст. 401 ГК РФ ответственность наступает только при наличии вины."
        ),
        "overcharge": (
            "В соответствии со ст. 15 ГК РФ порядок расчёта ущерба должен соответствовать реальным расходам "
            "на восстановление имущества по рыночным ценам. "
            "На основании ст. 401 ГК РФ ответственность наступает только при наличии вины арендатора."
        ),
        "unauthorized_charge": (
            "Согласно ст. 10 Закона РФ «О защите прав потребителей» потребитель вправе получить полную информацию "
            "об услуге и её стоимости до оказания услуги. "
            "Списание денежных средств без надлежащего уведомления и обоснования нарушает ст. 16 ЗоЗПП."
        ),
    }
    legal_base = _VIOLATION_LEGAL.get(
        violation_type,
        "На основании ст. 401 ГК РФ ответственность наступает только при наличии вины. "
        "Согласно ст. 10 ЗоЗПП потребитель вправе получить полную информацию об услуге.",
    )
    photo_note = (
        " Факт отсутствия повреждений до начала поездки подтверждён фотофиксацией из приложения / "
        "собственными фотографиями."
        if has_photo == "yes" else ""
    )
    data["calculated_legal_section"] = (
        legal_base
        + " В соответствии со ст. 14 ЗоЗПП исполнитель несёт ответственность за вред, причинённый вследствие "
        "недостатков услуги (неисправный автомобиль, отсутствие фиксации повреждений при выдаче)."
        + photo_note
    )

    data["calculated_amount_section"] = f"Сумма к возврату: {_fmt(claimed_amount)} руб."

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу вернуть списанную сумму в размере {_fmt(claimed_amount)} руб. "
        f"в течение 10 дней с даты получения настоящей претензии, а также предоставить документальное "
        f"подтверждение причин и расчёта ущерба. "
        f"В случае отказа оставляю за собой право обратиться в Роспотребнадзор и с иском в суд; "
        f"штраф 50% (ст. 13 ЗоЗПП), моральный вред, судебные расходы."
    )

    return data


def calculate_neighbor_flood(form_data: dict) -> dict:
    """Претензия о заливе квартиры соседом. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    apartment = str(data.get("apartment_address") or "").strip()
    incident_date_raw = str(data.get("incident_date") or "").strip()
    flood_source = str(data.get("flood_source") or "").strip()
    has_act = str(data.get("has_act") or "").strip()
    has_estimate = str(data.get("has_estimate") or "").strip()

    incident_d = _parse_date(incident_date_raw)
    incident_str = _fmt_date_ru(incident_d) if incident_d else incident_date_raw

    try:
        damage_amount = Decimal(str(data.get("damage_amount") or "0"))
    except Exception:
        damage_amount = Decimal("0")

    intro_parts = []
    if apartment:
        intro_parts.append(f"Пострадавшая квартира: {apartment}")
    intro_parts.append(f"Дата залива: {incident_str}")
    act_note = "Факт залива зафиксирован актом управляющей компании." if has_act == "yes" else "Ущерб зафиксирован фотоматериалами."
    intro_parts.append(act_note)
    data["calculated_intro_section"] = " ".join(intro_parts)

    legal_parts = [
        "На основании ст. 1064 ГК РФ лицо, причинившее вред, обязано возместить его в полном объёме.",
        "Согласно ст. 1082 ГК РФ возмещение вреда осуществляется путём возмещения убытков.",
        "В соответствии с ч. 4 ст. 30 ЖК РФ собственник помещения обязан поддерживать его в надлежащем состоянии, не допуская бесхозяйственного обращения с ним.",
    ]
    if flood_source == "management_company":
        legal_parts.append(
            "Согласно ст. 161 ЖК РФ управляющая организация несёт ответственность за надлежащее содержание общего имущества многоквартирного дома."
        )
    data["calculated_legal_section"] = " ".join(legal_parts)

    estimate_note = " на основании заключения независимого оценщика" if has_estimate == "yes" else " по рыночным ценам восстановительного ремонта"
    data["calculated_amount_section"] = (
        f"Размер причинённого ущерба составляет {_fmt(damage_amount)} руб.{estimate_note}."
    )

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу возместить причинённый ущерб в размере {_fmt(damage_amount)} руб. "
        f"в течение 10 дней с даты получения настоящей претензии. "
        f"В случае неисполнения требования в добровольном порядке оставляю за собой право обратиться в суд "
        f"с требованием о взыскании суммы ущерба, компенсации морального вреда (ст. 151 ГК РФ) и судебных расходов."
    )

    return data


def calculate_ddu_defects(form_data: dict) -> dict:
    """Претензия о недостатках по ДДУ. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    apartment = str(data.get("apartment_address") or "").strip()
    contract_num = str(data.get("contract_number") or "").strip()
    transfer_date_raw = str(data.get("transfer_date") or "").strip()
    elimination_period = str(data.get("elimination_period") or "30").strip()

    transfer_d = _parse_date(transfer_date_raw)
    transfer_str = _fmt_date_ru(transfer_d) if transfer_d else transfer_date_raw

    try:
        defects_amount = Decimal(str(data.get("defects_amount") or "0"))
    except Exception:
        defects_amount = Decimal("0")

    intro_parts = []
    if contract_num:
        intro_parts.append(f"Договор участия в долевом строительстве № {contract_num}")
    if apartment:
        intro_parts.append(f"объект — {apartment}")
    if transfer_str:
        intro_parts.append(f"акт приёма-передачи подписан {transfer_str}")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "." if intro_parts else ""

    data["calculated_legal_section"] = (
        "В соответствии с ч. 1 ст. 7 Федерального закона от 30.12.2004 № 214-ФЗ застройщик обязан передать "
        "участнику долевого строительства объект, качество которого соответствует условиям договора и "
        "обязательным требованиям. Согласно ч. 2 ст. 7 ФЗ-214 в случае, если объект построен с отступлениями "
        "от условий договора, дольщик вправе потребовать безвозмездного устранения недостатков в разумный срок. "
        "Гарантийный срок на объект составляет 5 лет (ч. 5 ст. 7 ФЗ-214). "
        "Согласно ст. 29 Закона РФ «О защите прав потребителей» потребитель вправе потребовать безвозмездного "
        "устранения недостатков оказанной услуги."
    )

    if defects_amount > 0:
        data["calculated_amount_section"] = (
            f"По предварительной оценке стоимость устранения выявленных недостатков составляет {_fmt(defects_amount)} руб."
        )
    else:
        data["calculated_amount_section"] = ""

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу устранить все перечисленные недостатки в срок {elimination_period} календарных дней "
        f"с даты получения настоящей претензии. "
        f"В случае неисполнения требования в добровольном порядке оставляю за собой право обратиться в суд с требованием: "
        f"безвозмездного устранения недостатков или возмещения расходов на их устранение, "
        f"неустойки в размере 1% от цены договора за каждый день просрочки, "
        f"компенсации морального вреда, штрафа в размере 50% от присуждённой суммы."
    )

    return data


def calculate_online_course(form_data: dict) -> dict:
    """Претензия онлайн-школе о возврате средств. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    school = str(data.get("school_name") or "").strip() or "онлайн-школе"
    course = str(data.get("course_name") or "").strip()
    contract_date_raw = str(data.get("contract_date") or "").strip()
    problem_type = str(data.get("problem_type") or "").strip()
    refund_request_date_raw = str(data.get("refund_request_date") or "").strip()

    contract_d = _parse_date(contract_date_raw)
    contract_str = _fmt_date_ru(contract_d) if contract_d else contract_date_raw

    refund_d = _parse_date(refund_request_date_raw)
    refund_str = _fmt_date_ru(refund_d) if refund_d else refund_request_date_raw

    try:
        course_price = Decimal(str(data.get("course_price") or "0"))
    except Exception:
        course_price = Decimal("0")
    try:
        claimed_amount = Decimal(str(data.get("claimed_amount") or "0"))
    except Exception:
        claimed_amount = Decimal("0")

    refund_amount = claimed_amount if claimed_amount > 0 else course_price

    intro_parts = [f"Онлайн-школа: {school}"]
    if course:
        intro_parts.append(f"курс: «{course}»")
    intro_parts.append(f"стоимость: {_fmt(course_price)} руб.")
    if contract_str:
        intro_parts.append(f"дата оплаты: {contract_str}")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    legal_parts = [
        "В соответствии с ч. 2 ст. 54 Федерального закона от 29.12.2012 № 273-ФЗ «Об образовании в Российской Федерации» "
        "при расторжении договора расчёт производится за фактически оказанные услуги.",
        "Согласно п. 24 Постановления Правительства РФ от 15.09.2020 № 1563 при расторжении договора исполнитель "
        "возвращает уплаченные средства за вычетом стоимости фактически оказанных услуг; фактические расходы должны быть "
        "документально подтверждены.",
        "На основании ст. 32 Закона РФ «О защите прав потребителей» потребитель вправе отказаться от исполнения договора "
        "об оказании услуг в любое время при условии оплаты исполнителю фактически понесённых им расходов.",
    ]
    if problem_type == "quality":
        legal_parts.append(
            "В соответствии со ст. 29 ЗоЗПП потребитель вправе потребовать соразмерного уменьшения цены услуги "
            "либо возмещения расходов по устранению недостатков, если услуга не соответствует условиям договора."
        )
    data["calculated_legal_section"] = " ".join(legal_parts)

    amount_parts = []
    if problem_type == "not_started":
        amount_parts.append(
            f"Обучение не началось, занятия не проводились — фактических расходов у исполнителя нет, "
            f"оснований для удержания средств не имеется. Сумма к возврату: {_fmt(refund_amount)} руб."
        )
    elif problem_type == "partial":
        amount_parts.append(
            f"Часть услуг оказана; сумма к возврату за неоказанные услуги: {_fmt(refund_amount)} руб. "
            f"Прошу предоставить детализацию фактически понесённых расходов с подтверждающими документами."
        )
    else:
        amount_parts.append(f"Сумма к возврату: {_fmt(refund_amount)} руб.")

    if refund_str:
        amount_parts.append(
            f"Запрос о возврате направлен {refund_str}; неустойка 3% в день начисляется с указанной даты (ч. 5 ст. 28 ЗоЗПП)."
        )
    data["calculated_amount_section"] = " ".join(amount_parts)

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу вернуть денежные средства в размере {_fmt(refund_amount)} руб. "
        f"в течение 10 дней с даты получения настоящей претензии. "
        f"В случае отказа оставляю за собой право обратиться в суд с требованием о взыскании суммы долга, "
        f"неустойки 3% за каждый день просрочки, компенсации морального вреда и штрафа 50% (ч. 6 ст. 13 ЗоЗПП)."
    )

    return data


def calculate_tour_operator(form_data: dict) -> dict:
    """Претензия туроператору о возврате средств. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_amount_section", "")
    data.setdefault("calculated_demand_section", "")

    operator = str(data.get("tour_operator") or "").strip() or "туроператору"
    destination = str(data.get("trip_destination") or "").strip()
    departure_date_raw = str(data.get("departure_date") or "").strip()
    contract_num = str(data.get("contract_number") or "").strip()
    violation_type = str(data.get("violation_type") or "").strip()

    departure_d = _parse_date(departure_date_raw)
    departure_str = _fmt_date_ru(departure_d) if departure_d else departure_date_raw

    try:
        tour_price = Decimal(str(data.get("tour_price") or "0"))
    except Exception:
        tour_price = Decimal("0")
    try:
        refunded_amount = Decimal(str(data.get("refunded_amount") or "0"))
    except Exception:
        refunded_amount = Decimal("0")

    refund_due = tour_price - refunded_amount if refunded_amount > 0 else tour_price

    intro_parts = [f"Туроператор: {operator}"]
    if destination:
        intro_parts.append(f"направление: {destination}")
    if departure_str:
        intro_parts.append(f"дата вылета: {departure_str}")
    intro_parts.append(f"стоимость тура: {_fmt(tour_price)} руб.")
    if contract_num:
        intro_parts.append(f"договор № {contract_num}")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    if violation_type in ("operator_cancelled", "changed_conditions"):
        legal_text = (
            "В соответствии со ст. 10 Федерального закона от 24.11.1996 № 132-ФЗ «Об основах туристской деятельности "
            "в Российской Федерации» при существенном изменении обстоятельств, в том числе невозможности совершения тура "
            "по вине туроператора или изменения условий путешествия, турист вправе отказаться от тура и получить полный "
            "возврат уплаченных средств. "
            "Согласно ст. 10.1 ФЗ № 132-ФЗ туроператор обязан вернуть денежные средства в течение 10 дней с момента "
            "предъявления требования."
        )
    else:
        legal_text = (
            "На основании ст. 32 Закона РФ «О защите прав потребителей» и ст. 782 ГК РФ потребитель вправе отказаться "
            "от исполнения договора об оказании услуг в любое время при условии оплаты исполнителю фактически понесённых им "
            "расходов. Фактические расходы должны быть документально подтверждены; удержание без подтверждения расходов незаконно."
        )
    legal_text += (
        " В соответствии с ч. 5 ст. 28 ЗоЗПП нарушение срока возврата влечёт неустойку 3% от суммы долга за каждый день "
        "просрочки. При обращении в суд — штраф 50% от присуждённой суммы (ч. 6 ст. 13 ЗоЗПП)."
    )
    data["calculated_legal_section"] = legal_text

    if refunded_amount > 0:
        data["calculated_amount_section"] = (
            f"Частично возвращено {_fmt(refunded_amount)} руб. Остаток к возврату: {_fmt(refund_due)} руб."
        )
    else:
        data["calculated_amount_section"] = (
            f"Сумма к возврату: {_fmt(tour_price)} руб."
        )

    data["calculated_demand_section"] = (
        f"На основании изложенного прошу вернуть денежные средства в размере {_fmt(refund_due)} руб. "
        f"в течение 10 дней с даты получения настоящей претензии. "
        f"В случае отказа оставляю за собой право обратиться в суд с требованием о взыскании суммы долга, "
        f"неустойки 3% за каждый день просрочки, компенсации морального вреда и штрафа 50% (ч. 6 ст. 13 ЗоЗПП)."
    )

    return data


def calculate_bank(form_data: dict) -> dict:
    """Претензия в банк: незаконная комиссия, навязанная страховка, блокировка счёта."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_demand_section", "")

    bank = str(data.get("bank_name") or "").strip() or "банку"
    contract_num = str(data.get("contract_number") or "").strip()
    violation_date_raw = str(data.get("violation_date") or "").strip()
    violation_type = str(data.get("violation_type") or "").strip()
    demand = str(data.get("demand") or "").strip()

    violation_d = _parse_date(violation_date_raw)
    violation_str = _fmt_date_ru(violation_d) if violation_d else violation_date_raw

    try:
        amount = Decimal(str(data.get("amount") or "0"))
    except Exception:
        amount = Decimal("0")

    intro_parts = [f"Банк: {bank}"]
    if contract_num:
        intro_parts.append(f"договор/счёт № {contract_num}")
    if violation_str:
        intro_parts.append(f"дата события: {violation_str}")
    if amount > 0:
        intro_parts.append(f"спорная сумма: {_fmt(amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    if violation_type == "insurance":
        data["calculated_legal_section"] = (
            "В соответствии со ст. 7 Федерального закона от 21.12.2013 № 353-ФЗ «О потребительском кредите (займе)» "
            "страхование при выдаче кредита является добровольным; навязывание страховки как обязательного условия "
            "противоречит закону. "
            "Согласно Указанию Банка России от 20.11.2015 № 3854-У потребитель вправе отказаться от договора "
            "добровольного страхования в течение 30 рабочих дней с момента его заключения (период охлаждения) "
            "и получить полный возврат уплаченной страховой премии. "
            "В соответствии со ст. 16 Закона РФ «О защите прав потребителей» условия договора, ущемляющие права "
            "потребителя, признаются недействительными."
        )
    elif violation_type == "block":
        data["calculated_legal_section"] = (
            "В соответствии с ч. 5.2 ст. 7 Федерального закона от 07.08.2001 № 115-ФЗ банк обязан уведомить клиента "
            "об ограничении операций не позднее 5 рабочих дней и сообщить причины при наличии такой возможности. "
            "Согласно ч. 13.1 ст. 7 ФЗ № 115-ФЗ клиент вправе представить документы, подтверждающие законность "
            "происхождения денежных средств. "
            "На основании ст. 845 ГК РФ банк обязан исполнять распоряжения клиента о перечислении и выдаче средств; "
            "ст. 856 ГК РФ предусматривает ответственность банка за незаконное удержание денежных средств."
        )
    elif violation_type == "commission":
        data["calculated_legal_section"] = (
            "В соответствии со ст. 16 Закона РФ «О защите прав потребителей» условия договора, обязывающие потребителя "
            "оплачивать комиссии, не предусмотренные законом, признаются недействительными, а уплаченные суммы подлежат "
            "возврату. "
            "Согласно ст. 168 ГК РФ сделка, нарушающая требования закона, является ничтожной. "
            "На основании ст. 1102 ГК РФ банк обязан вернуть неосновательно полученные денежные средства."
        )
    else:
        data["calculated_legal_section"] = (
            "В соответствии с Законом РФ «О защите прав потребителей» и нормами ГК РФ банк обязан "
            "действовать в интересах клиента и возвратить неправомерно полученные денежные средства."
        )

    if demand == "return_insurance":
        demand_text = (
            f"На основании изложенного прошу вернуть страховую премию в размере {_fmt(amount)} руб. "
            f"в течение 30 рабочих дней с даты получения настоящей претензии."
        )
    elif demand == "unblock":
        demand_text = (
            "На основании изложенного прошу снять ограничения с банковского счёта/карты "
            "в течение 10 рабочих дней с даты получения настоящей претензии."
        )
    elif demand == "return_commission":
        demand_text = (
            f"На основании изложенного прошу вернуть незаконно удержанную комиссию в размере {_fmt(amount)} руб. "
            f"в течение 30 дней с даты получения настоящей претензии."
        )
    else:
        demand_text = (
            f"На основании изложенного прошу рассмотреть настоящую претензию и удовлетворить "
            f"требование в течение 30 дней с даты получения. "
        )

    demand_text += (
        " В случае отказа или игнорирования оставляю за собой право обратиться с жалобой в Банк России "
        "(cbr.ru) и Роспотребнадзор, а также с иском в суд."
    )
    data["calculated_demand_section"] = demand_text

    return data


def calculate_bank_block(form_data: dict) -> dict:
    """Заявление о снятии ограничений по 115-ФЗ. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_notification_section", "")
    data.setdefault("calculated_demand_section", "")

    bank = str(data.get("bank_name") or "").strip() or "банку"
    account_number = str(data.get("account_number") or "").strip()
    violation_date_raw = str(data.get("violation_date") or "").strip()
    block_reason = str(data.get("block_reason") or "").strip()
    bank_notification = str(data.get("bank_notification") or "").strip()

    violation_d = _parse_date(violation_date_raw)
    violation_str = _fmt_date_ru(violation_d) if violation_d else violation_date_raw

    try:
        amount = Decimal(str(data.get("amount") or "0"))
    except Exception:
        amount = Decimal("0")

    intro_parts = [f"Банк: {bank}"]
    if account_number:
        intro_parts.append(f"счёт/карта: {account_number}")
    if violation_str:
        intro_parts.append(f"дата блокировки: {violation_str}")
    if amount > 0:
        intro_parts.append(f"сумма заблокированных средств: {_fmt(amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    block_reason_map = {
        "suspicious_operations": "подозрительные операции (без конкретики)",
        "source_of_funds": "не подтверждено происхождение средств",
        "115fz_monitoring": "финансовый мониторинг / 115-ФЗ",
        "other": "причина не объяснена",
    }
    reason_text = block_reason_map.get(block_reason, "причина не указана")

    data["calculated_legal_section"] = (
        "В соответствии с ч. 13.1 ст. 7 Федерального закона от 07.08.2001 № 115-ФЗ «О противодействии легализации "
        "(отмыванию) доходов, полученных преступным путём, и финансированию терроризма» клиент вправе представить в банк "
        "документы и сведения, подтверждающие законность происхождения денежных средств. "
        "Согласно ч. 13.2 ст. 7 ФЗ № 115-ФЗ банк обязан рассмотреть представленные документы и сообщить о принятом решении "
        "в течение 10 рабочих дней. "
        "На основании ст. 845 ГК РФ банк обязан исполнять распоряжения клиента о перечислении и выдаче средств со счёта; "
        "ст. 856 ГК РФ предусматривает ответственность банка за незаконное удержание денежных средств в виде уплаты "
        "процентов по ст. 395 ГК РФ."
    )

    if bank_notification == "not_notified":
        data["calculated_notification_section"] = (
            f"Помимо этого, банк нарушил ч. 5.2 ст. 7 ФЗ № 115-ФЗ: клиент не был уведомлён об ограничении операций "
            f"в установленный срок (не позднее 5 рабочих дней). Причина блокировки по версии банка: {reason_text}."
        )
    else:
        data["calculated_notification_section"] = (
            f"Причина блокировки по версии банка: {reason_text}."
        )

    data["calculated_demand_section"] = (
        "На основании изложенного прошу снять ограничения с банковского счёта/карты "
        "в течение 10 рабочих дней с даты подачи настоящего заявления. "
        "В случае отказа или бездействия оставляю за собой право обратиться с жалобой в Банк России "
        "(Интернет-приёмная на cbr.ru) и в Росфинмониторинг; при причинении убытков — с иском в суд "
        "(ГК РФ ст. 856, 395)."
    )

    return data


def calculate_utility(form_data: dict) -> dict:
    """Претензия в УК/ТСЖ: перерасчёт, некачественные услуги, ремонт. Pre-renders секции."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_demand_section", "")

    company = str(data.get("company_name") or "").strip() or "управляющей компании"
    apartment = str(data.get("apartment_address") or "").strip()
    violation_period = str(data.get("violation_period") or "").strip()
    violation_type = str(data.get("violation_type") or "").strip()
    demand = str(data.get("demand") or "").strip()

    try:
        disputed_amount = Decimal(str(data.get("disputed_amount") or "0"))
    except Exception:
        disputed_amount = Decimal("0")

    intro_parts = [f"УК/ТСЖ: {company}"]
    if apartment:
        intro_parts.append(f"адрес: {apartment}")
    if violation_period:
        intro_parts.append(f"период нарушения: {violation_period}")
    if disputed_amount > 0:
        intro_parts.append(f"сумма к перерасчёту: {_fmt(disputed_amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "."

    base_legal = (
        "В соответствии с ч. 1 ст. 161 Жилищного кодекса РФ управление многоквартирным домом должно обеспечивать "
        "благоприятные и безопасные условия проживания граждан, надлежащее содержание общего имущества. "
    )

    if violation_type == "overcharge":
        data["calculated_legal_section"] = (
            base_legal
            + "Согласно ст. 157 ЖК РФ размер платы за коммунальные услуги рассчитывается исходя из объёма потребляемых "
            "коммунальных услуг, определяемого по показаниям приборов учёта. "
            "Постановление Правительства РФ от 06.05.2011 № 354 устанавливает порядок расчёта и перерасчёта платы "
            "за коммунальные услуги; начисления сверх норматива без оснований нарушают п. 42–44 данного постановления. "
            "На основании ст. 16 ЗоЗПП условия, ущемляющие права потребителя, недействительны."
        )
    elif violation_type == "poor_service":
        data["calculated_legal_section"] = (
            base_legal
            + "Постановление Правительства РФ от 06.05.2011 № 354 предусматривает ответственность исполнителя за "
            "предоставление коммунальных услуг ненадлежащего качества; при этом производится перерасчёт платы "
            "(разделы IX–X постановления). "
            "Согласно ч. 2.3 ст. 161 ЖК РФ управляющая организация несёт ответственность перед собственниками "
            "за оказание всех услуг и выполнение работ по надлежащему содержанию и ремонту общего имущества."
        )
    elif violation_type == "no_repair":
        data["calculated_legal_section"] = (
            base_legal
            + "Постановление Правительства РФ от 13.08.2006 № 491 устанавливает минимальный перечень работ по "
            "содержанию и ремонту общего имущества многоквартирного дома, обязательных для управляющей организации. "
            "Отказ от проведения работ, включённых в минимальный перечень, является нарушением ст. 161 ЖК РФ и "
            "влечёт административную ответственность по ст. 7.22 КоАП РФ."
        )
    else:
        data["calculated_legal_section"] = (
            base_legal
            + "Управляющая компания обязана надлежащим образом исполнять договор управления и устранять нарушения "
            "в установленные сроки."
        )

    if demand == "recalculate":
        if disputed_amount > 0:
            demand_text = (
                f"На основании изложенного прошу произвести перерасчёт платы за коммунальные услуги "
                f"и вернуть излишне уплаченные {_fmt(disputed_amount)} руб. в течение 30 дней."
            )
        else:
            demand_text = (
                "На основании изложенного прошу произвести перерасчёт платы за коммунальные услуги "
                "в течение 30 дней с даты получения настоящей претензии."
            )
    elif demand == "fix":
        demand_text = (
            "На основании изложенного прошу устранить допущенные нарушения "
            "в течение 30 дней с даты получения настоящей претензии."
        )
    else:
        if disputed_amount > 0:
            demand_text = (
                f"На основании изложенного прошу произвести перерасчёт и вернуть {_fmt(disputed_amount)} руб., "
                f"а также устранить допущенные нарушения в течение 30 дней с даты получения настоящей претензии."
            )
        else:
            demand_text = (
                "На основании изложенного прошу произвести перерасчёт и устранить допущенные нарушения "
                "в течение 30 дней с даты получения настоящей претензии."
            )

    demand_text += (
        " При неисполнении оставляю за собой право обратиться с жалобой в Государственную жилищную инспекцию, "
        "прокуратуру, а также с иском в суд."
    )
    data["calculated_demand_section"] = demand_text

    return data


def calculate_gibdd(form_data: dict) -> dict:
    """Жалоба на постановление ГИБДД. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_legal_section", "")
    data.setdefault("calculated_objection_section", "")
    data.setdefault("calculated_demand_section", "")

    fine_number = str(data.get("fine_number") or "").strip()
    violation_date_raw = str(data.get("violation_date") or "").strip()
    violation_place = str(data.get("violation_place") or "").strip()
    vehicle = str(data.get("vehicle") or "").strip()
    violation_article = str(data.get("violation_article") or "").strip()
    objection_reason = str(data.get("objection_reason") or "").strip()
    additional_desc = str(data.get("additional_desc") or "").strip()
    appeal_to = str(data.get("appeal_to") or "").strip()

    violation_d = _parse_date(violation_date_raw)
    violation_str = _fmt_date_ru(violation_d) if violation_d else violation_date_raw

    try:
        amount = Decimal(str(data.get("amount") or "0"))
    except Exception:
        amount = Decimal("0")

    intro_parts = []
    if fine_number:
        intro_parts.append(f"постановление № {fine_number}")
    if violation_str:
        intro_parts.append(f"дата нарушения: {violation_str}")
    if violation_place:
        intro_parts.append(f"место: {violation_place}")
    if vehicle:
        intro_parts.append(f"ТС: {vehicle}")
    if violation_article:
        intro_parts.append(f"статья: {violation_article}")
    if amount > 0:
        intro_parts.append(f"штраф: {_fmt(amount)} руб.")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "." if intro_parts else ""

    data["calculated_legal_section"] = (
        "В соответствии со ст. 30.1 КоАП РФ постановление по делу об административном правонарушении может быть "
        "обжаловано вышестоящему должностному лицу либо в суд. "
        "Согласно ст. 30.3 КоАП РФ жалоба подаётся в течение 10 суток со дня вручения или получения копии постановления. "
        "На основании ст. 1.5 КоАП РФ лицо подлежит административной ответственности только за те административные "
        "правонарушения, в отношении которых установлена его вина; все неустранимые сомнения трактуются в его пользу."
    )

    objection_map = {
        "not_driving": (
            "В соответствии с ч. 2 ст. 2.6.1 КоАП РФ собственник транспортного средства освобождается от "
            "административной ответственности, если докажет, что в момент фиксации нарушения ТС находилось "
            "в пользовании другого лица. К настоящей жалобе прилагаются документы, подтверждающие данное обстоятельство "
            "(доверенность / договор аренды / заявление об угоне)."
        ),
        "no_violation": (
            "В соответствии с п. 1 ст. 24.5 КоАП РФ производство по делу об административном правонарушении не может "
            "быть начато, а начатое производство подлежит прекращению при отсутствии события административного "
            "правонарушения. Обстоятельства, изложенные в постановлении, не соответствуют действительности."
        ),
        "camera_error": (
            "Согласно ст. 26.8 КоАП РФ показания специальных технических средств оцениваются в совокупности с другими "
            "доказательствами по делу. Фиксация нарушения произведена техническим средством, данные которого вызывают "
            "сомнения в достоверности; погрешность прибора должна быть подтверждена действующим сертификатом поверки. "
            "В соответствии со ст. 26.11 КоАП РФ неустранимые сомнения трактуются в пользу лица, привлекаемого "
            "к ответственности."
        ),
        "procedural": (
            "В соответствии со ст. 28.2 КоАП РФ нарушения при составлении протокола об административном "
            "правонарушении являются существенными и влекут признание постановления незаконным. "
            "Согласно ст. 4.5 КоАП РФ постановление по делу об административном правонарушении не может быть "
            "вынесено по истечении двух месяцев (по делу, рассматриваемому судьёй, — трёх месяцев) со дня "
            "совершения административного правонарушения."
        ),
        "other": (
            "В соответствии со ст. 24.1 КоАП РФ задачами производства по делам об административных "
            "правонарушениях являются всестороннее, полное, объективное и своевременное выяснение обстоятельств "
            "каждого дела. Вынесенное постановление не соответствует данным требованиям."
        ),
    }
    data["calculated_objection_section"] = objection_map.get(
        objection_reason,
        "Постановление является незаконным и подлежит отмене.",
    )

    if additional_desc:
        data["calculated_objection_section"] += f" {additional_desc}"

    if appeal_to == "court":
        appeal_phrase = "в суд"
    else:
        appeal_phrase = "вышестоящему должностному лицу ГИБДД"

    fine_ref = f"постановление № {fine_number}" if fine_number else "данное постановление"
    data["calculated_demand_section"] = (
        f"На основании изложенного прошу отменить {fine_ref} и прекратить производство по делу "
        f"на основании п. 1 ст. 24.5 КоАП РФ. "
        f"Жалоба направлена {appeal_phrase}. "
        f"К жалобе прилагаются: копия постановления, копия СТС/ПТС."
    )

    return data


def calculate_debt_collector(form_data: dict) -> dict:
    """Жалоба в ФССП на незаконные действия коллекторов. Pre-renders секции для python_template."""
    data = dict(form_data)
    data.setdefault("calculated_intro_section", "")
    data.setdefault("calculated_violations_section", "")
    data.setdefault("calculated_recordings_section", "")
    data.setdefault("calculated_demand_section", "")

    creditor = str(data.get("creditor_name") or "").strip()
    collector = str(data.get("collector_name") or "").strip()
    debt_desc = str(data.get("debt_desc") or "").strip()
    violation_types = str(data.get("violation_types") or "").strip()
    has_recordings = str(data.get("has_recordings") or "").strip()
    first_contact_date_raw = str(data.get("first_contact_date") or "").strip()

    first_d = _parse_date(first_contact_date_raw)
    first_str = _fmt_date_ru(first_d) if first_d else first_contact_date_raw

    intro_parts = []
    if creditor:
        intro_parts.append(f"кредитор: {creditor}")
    if debt_desc:
        intro_parts.append(f"долг: {debt_desc}")
    if collector:
        intro_parts.append(f"коллекторская организация: {collector}")
    if first_str:
        intro_parts.append(f"преследование началось с: {first_str}")
    data["calculated_intro_section"] = ", ".join(intro_parts) + "." if intro_parts else ""

    violation_map = {
        "night_calls": (
            "1. Коллекторы осуществляют звонки в запрещённое законом время. "
            "В соответствии с ч. 3 ст. 7 Федерального закона от 03.07.2016 № 230-ФЗ взаимодействие с должником "
            "в рабочие дни допускается с 08:00 до 22:00 по местному времени, в выходные и праздничные дни — "
            "с 09:00 до 20:00. Зафиксированные звонки выходят за пределы указанных временных ограничений."
        ),
        "frequency": (
            "1. Коллекторы нарушают установленные лимиты частоты взаимодействия. "
            "Согласно ч. 3 ст. 7 ФЗ № 230-ФЗ допускается не более 1 звонка в сутки, 2 звонков в неделю "
            "и 8 звонков в месяц. Фактическое количество звонков превышает установленные нормы."
        ),
        "threats": (
            "1. Коллекторы применяют психологическое давление, угрозы и иные противоправные методы воздействия. "
            "В соответствии с ч. 2 ст. 6 ФЗ № 230-ФЗ запрещается применять к должнику физическую силу, угрожать "
            "применением физической силы, причинением вреда здоровью, имуществу, а также оказывать психологическое "
            "давление, в том числе угрожать уголовным преследованием или разглашением информации."
        ),
        "third_parties": (
            "1. Коллекторы осуществляют взаимодействие с третьими лицами (родственниками, коллегами, работодателем) "
            "без письменного согласия должника. "
            "Согласно ч. 5 ст. 4 ФЗ № 230-ФЗ такое взаимодействие допускается только при наличии "
            "письменного согласия должника, которое им не давалось."
        ),
        "no_intro": (
            "1. Коллекторы не представляются при звонках, не называют организацию и кредитора. "
            "В соответствии с ч. 4 ст. 7 ФЗ № 230-ФЗ при взаимодействии посредством телефонных переговоров "
            "взыскатель обязан сообщить свои фамилию, имя, отчество, наименование кредитора и коллекторской "
            "организации, а также сведения о наличии просроченной задолженности."
        ),
        "other": (
            "1. Коллекторская организация допускает иные нарушения требований ФЗ № 230-ФЗ, "
            "подробно описанные в прилагаемых материалах."
        ),
    }
    data["calculated_violations_section"] = violation_map.get(
        violation_types,
        "Коллекторская организация нарушает требования ФЗ № 230-ФЗ.",
    )

    if has_recordings == "yes":
        data["calculated_recordings_section"] = (
            "Факты нарушений подтверждены аудиозаписями звонков, которые прилагаются к настоящей жалобе."
        )
    else:
        data["calculated_recordings_section"] = ""

    data["calculated_demand_section"] = (
        "На основании изложенного прошу провести проверку деятельности коллекторской организации "
        "и привлечь её к административной ответственности по ч. 1 ст. 14.57 КоАП РФ "
        "(штраф от 50 000 до 500 000 руб.). "
        "Настоящая жалоба направлена одновременно в Банк России и в прокуратуру. "
        "К жалобе прилагаются: скриншоты звонков"
        + (", аудиозаписи разговоров" if has_recordings == "yes" else "")
        + "."
    )

    return data


def calculate_mfo(form_data: dict) -> dict:
    """Претензия к МФО: излишки процентов при ставке > 1%/день (ФЗ №151 ст. 9)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    mfo_name = str(data.get("mfo_name") or "").strip()
    loan_amount_str = str(data.get("loan_amount") or "0")
    daily_rate_str = str(data.get("daily_rate") or "0")
    loan_date = _ru_date(data.get("loan_date"))
    violation_type = str(data.get("violation_type") or "").strip()

    try:
        loan_amount = Decimal(loan_amount_str)
        daily_rate = Decimal(daily_rate_str)
    except Exception:
        loan_amount = Decimal("0")
        daily_rate = Decimal("0")

    # Intro
    intro = "Мной получен микрозаём"
    if mfo_name:
        intro += f" у {mfo_name}"
    if loan_date:
        intro += f" от {loan_date}"
    if loan_amount > 0:
        intro += f" в размере {_fmt(loan_amount)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    # Violation
    if violation_type == "illegal_rate" and daily_rate > Decimal("1.0"):
        excess_rate = daily_rate - Decimal("1.0")
        loan_date_obj = _parse_date(data.get("loan_date"))
        days_since_loan = 0
        if loan_date_obj:
            days_since_loan = max((date.today() - loan_date_obj).days, 0)

        excess_amount = loan_amount * excess_rate / Decimal("100") * Decimal(days_since_loan)
        excess_amount = excess_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        data["calculated_violation_section"] = (
            f"Микрофинансовая организация взимает процент в размере {_fmt(daily_rate)}% в день, "
            f"что превышает установленный законом кэп 1% в день (ФЗ №151 ст. 9)."
        )
        data["calculated_amount_section"] = (
            f"Излишний процент: ({_fmt(daily_rate)}% − 1%) × {_fmt(loan_amount)} руб. × {days_since_loan} дн. = "
            f"{_fmt(excess_amount)} руб."
        )
    else:
        data["calculated_violation_section"] = (
            f"Проверена ставка по микрозайму: {_fmt(daily_rate)}% в день."
        )
        data["calculated_amount_section"] = ""

    data["calculated_demand_section"] = (
        "На основании изложенного прошу пересчитать задолженность с учётом установленного закономом "
        "максимального процента (1% в день по ФЗ №151 ст. 9) и возвратить излишне взысканные суммы "
        "в течение десяти календарных дней с даты получения настоящей претензии."
    )

    return data


def calculate_gibdd_camera(form_data: dict) -> dict:
    """Претензия ГИБДД: срок обжалования 10 дней (КоАП ст. 30.3)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_deadline_section"] = ""
    data["calculated_demand_section"] = ""

    fine_date = _parse_date(data.get("fine_date"))
    fine_amount_str = str(data.get("fine_amount") or "0")
    fine_number = str(data.get("fine_number") or "").strip()
    vehicle_number = str(data.get("vehicle_number") or "").strip()
    violation_type = str(data.get("violation_type") or "").strip()

    try:
        fine_amount = Decimal(fine_amount_str)
    except Exception:
        fine_amount = Decimal("0")

    # Intro
    intro = "Мною получено постановление"
    if fine_number:
        intro += f" № {fine_number}"
    if fine_date:
        intro += f" от {_fmt_date_ru(fine_date)}"
    if vehicle_number:
        intro += f" в отношении автомобиля {vehicle_number}"
    if fine_amount > 0:
        intro += f" о наложении штрафа на сумму {_fmt(fine_amount)} руб"
    intro += "."

    # Основание для несогласия — по типу нарушения (русский текст, не сырое значение)
    violation_map = {
        "wrong_owner": "Я не являюсь собственником автомобиля, зафиксированного в момент нарушения.",
        "not_driving": "В момент фиксации нарушения я не управлял указанным транспортным средством — оно находилось во владении другого лица.",
        "camera_error": "Камера зафиксировала нарушение некорректно: данные о транспортном средстве или обстоятельствах нарушения недостоверны.",
        "no_sign": "Дорожный знак или разметка, ограничивающие движение, в месте фиксации отсутствовали либо не были видны.",
    }
    reason = violation_map.get(violation_type, "")
    if reason:
        intro += f" {reason}"
    data["calculated_intro_section"] = intro

    # Deadline
    if fine_date:
        deadline_date = fine_date + timedelta(days=10)
        deadline_str = _fmt_date_ru(deadline_date)
        data["calculated_deadline_section"] = (
            f"Срок обжалования по КоАП ст. 30.3: 10 дней со дня получения постановления. "
            f"Данная претензия подается до {deadline_str} включительно."
        )
    else:
        data["calculated_deadline_section"] = (
            "Срок обжалования по КоАП ст. 30.3 составляет 10 дней со дня получения постановления."
        )

    data["calculated_demand_section"] = (
        "На основании изложенного прошу отменить постановление о привлечении меня к административной ответственности "
        "в соответствии с КоАП РФ ст. 2.6.1 (я не являюсь собственником в момент нарушения) и КоАП РФ ст. 30.1–30.3 "
        "(порядок обжалования). "
        "Прошу рассмотреть жалобу в установленный законом срок."
    )

    return data


def calculate_repair_apartment(form_data: dict) -> dict:
    """Претензия подрядчику за ремонт: неустойка 3%/день (ЗоЗПП ст. 28)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_penalty"] = ""
    data["calculated_demand_section"] = ""

    contractor_name = str(data.get("contractor_name") or "").strip()
    contract_date = _ru_date(data.get("contract_date"))
    contract_amount_str = str(data.get("contract_amount") or "0")
    defect_discovery_date = _parse_date(data.get("defect_discovery_date"))

    try:
        contract_amount = Decimal(contract_amount_str)
    except Exception:
        contract_amount = Decimal("0")

    # Intro
    intro = "Между мной и"
    if contractor_name:
        intro += f" {contractor_name}"
    if contract_date:
        intro += f" заключен договор подряда от {contract_date}"
    else:
        intro += " заключен договор подряда"
    if contract_amount > 0:
        intro += f" на сумму {_fmt(contract_amount)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    # Violation
    data["calculated_violation_section"] = "При выполнении ремонтных работ выявлены серьёзные недостатки, которые подрядчик отказывается устранять."

    # Penalty
    if defect_discovery_date and contract_amount > 0:
        delay_days = max((date.today() - defect_discovery_date).days, 0)
        penalty = min(contract_amount * Decimal("0.03") * Decimal(delay_days), contract_amount)
        penalty = penalty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        data["calculated_penalty"] = _fmt(penalty)
        data["calculated_demand_section"] = (
            f"На основании ст. 28 ЗоЗПП за {delay_days} дней просрочки устранения недостатков "
            f"подрядчик должен уплатить неустойку в размере 3% × {_fmt(contract_amount)} руб. × {delay_days} дн. = "
            f"{_fmt(penalty)} руб. "
            f"Прошу выплатить неустойку и безвозмездно устранить недостатки в течение 10 дней."
        )
    else:
        data["calculated_demand_section"] = (
            "На основании ст. 28, 29 ЗоЗПП прошу безвозмездно устранить выявленные недостатки "
            "в течение 10 дней с даты получения настоящей претензии. При отказе буду требовать "
            "уменьшение стоимости работ или расторжение договора и возврат денег."
        )

    return data


def calculate_online_shop_delivery(form_data: dict) -> dict:
    """Претензия магазину: неустойка 0.5%/день (не доставил) или 1%/день (не то) (ЗоЗПП ст. 23.1)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_penalty"] = ""
    data["calculated_demand_section"] = ""

    shop_name = str(data.get("shop_name") or "").strip()
    order_date = _ru_date(data.get("order_date"))
    order_number = str(data.get("order_number") or "").strip()
    order_amount_str = str(data.get("order_amount") or "0")
    problem_type = str(data.get("problem_type") or "").strip()

    try:
        order_amount = Decimal(order_amount_str)
    except Exception:
        order_amount = Decimal("0")

    # Intro
    intro = "Мной оформлен заказ"
    if shop_name:
        intro += f" в интернет-магазине {shop_name}"
    if order_date:
        intro += f" от {order_date}"
    if order_number:
        intro += f" (номер заказа {order_number})"
    if order_amount > 0:
        intro += f" на сумму {_fmt(order_amount)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    # Penalty rate depends on problem type
    rate = Decimal("0.01")  # 1% по умолчанию
    rate_desc = "1%"
    if problem_type == "not_delivered":
        rate = Decimal("0.005")  # 0.5% (ст. 23.1)
        rate_desc = "0.5%"

    order_date_obj = _parse_date(data.get("order_date"))
    if order_date_obj and order_amount > 0:
        delay_days = max((date.today() - order_date_obj).days, 0)
        penalty = min(order_amount * rate * Decimal(delay_days), order_amount)
        penalty = penalty.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        data["calculated_penalty"] = _fmt(penalty)

        if problem_type == "not_delivered":
            data["calculated_demand_section"] = (
                f"На основании ст. 23.1 ЗоЗПП магазин должен уплатить неустойку за непередачу товара: "
                f"{rate_desc} × {_fmt(order_amount)} руб. × {delay_days} дн. = {_fmt(penalty)} руб., "
                f"а также полностью вернуть сумму предоплаты в течение 10 дней."
            )
        else:
            data["calculated_demand_section"] = (
                f"На основании ст. 23 ЗоЗПП магазин должен уплатить неустойку за ненадлежащее качество товара: "
                f"{rate_desc} × {_fmt(order_amount)} руб. × {delay_days} дн. = {_fmt(penalty)} руб., "
                f"а также заменить товар или вернуть деньги в течение 10 дней."
            )
    else:
        data["calculated_demand_section"] = (
            "На основании ст. 23.1, 18 ЗоЗПП прошу в течение 10 дней либо доставить товар, "
            "либо вернуть полную стоимость заказа. При отказе буду требовать неустойку и возмещение убытков."
        )

    return data


def calculate_education_refund(form_data: dict) -> dict:
    """Претензия школе: пропорциональный возврат за курсы (ЗоЗПП ст. 32)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    school_name = str(data.get("school_name") or "").strip()
    course_name = str(data.get("course_name") or "").strip()
    paid_amount_str = str(data.get("paid_amount") or "0")
    total_classes_str = str(data.get("total_classes") or "0")
    attended_classes_str = str(data.get("attended_classes") or "0")

    try:
        paid_amount = Decimal(paid_amount_str)
        total_classes = int(total_classes_str) if total_classes_str else 0
        attended_classes = int(attended_classes_str) if attended_classes_str else 0
    except Exception:
        paid_amount = Decimal("0")
        total_classes = 0
        attended_classes = 0

    # Intro
    intro = "Мной приобретено обучение по курсу"
    if course_name:
        intro += f" «{course_name}»"
    if school_name:
        intro += f", организованному {school_name}"
    if paid_amount > 0:
        intro += f", стоимостью {_fmt(paid_amount)} руб."
    intro += "."
    data["calculated_intro_section"] = intro

    # Calculate refund
    if total_classes > 0:
        unattended = total_classes - attended_classes
        refund = paid_amount / Decimal(total_classes) * Decimal(unattended)
    else:
        # Guard: if no total_classes, refund full amount
        refund = paid_amount
    refund = refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    data["calculated_amount_section"] = (
        f"Рассчёт возврата по ст. 32 ЗоЗПП: "
        f"{_fmt(paid_amount)} руб. ÷ {total_classes} занятий × {total_classes - attended_classes} непосещённых = "
        f"{_fmt(refund)} руб. к возврату."
    )

    data["calculated_demand_section"] = (
        f"На основании ст. 32 ЗоЗПП (право потребителя отказаться от услуги) и ст. 28 (неустойка за задержку) "
        f"прошу вернуть мне {_fmt(refund)} руб. в течение 10 дней с даты получения претензии."
    )

    return data


def calculate_university_admission(form_data: dict) -> dict:
    """Претензия вузу: нарушение прав при поступлении (ФЗ №273 ст. 55)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_demand_section"] = ""

    university_name = str(data.get("university_name") or "").strip()
    specialty = str(data.get("specialty") or "").strip()
    violation_type = str(data.get("violation_type") or "").strip()
    application_date = _ru_date(data.get("application_date"))

    # Intro
    intro = "Мной поданы документы на поступление"
    if specialty:
        intro += f" по специальности {specialty}"
    if university_name:
        intro += f" в {university_name}"
    if application_date:
        intro += f" {application_date}"
    intro += "."
    data["calculated_intro_section"] = intro

    # Demand (no calculation, just format)
    violation_map = {
        "not_admitted": "несоответствию правилам приёма либо ошибке при обработке документов",
        "documents_lost": "потере поданных мной документов",
        "wrong_ranking": "ошибке в ранжировании абитуриентов",
        "deadline_missed": "нарушению установленных сроков рассмотрения документов",
    }

    violation_desc = violation_map.get(violation_type, "нарушению прав при поступлении")

    data["calculated_demand_section"] = (
        f"На основании ФЗ №273 ст. 55 (право на обучение на принципах равных условий) "
        f"и КАС РФ ст. 218 (оспаривание действий организаций) "
        f"в связи с {violation_desc} прошу: "
        f"(1) провести проверку решения об отказе в приёме; "
        f"(2) издать приказ о зачислении либо возобновить рассмотрение заявки. "
        f"В противном случае буду оспаривать решение в административном суде."
    )

    return data


def calculate_ip_employer(form_data: dict) -> dict:
    """Претензия ИП-работодателю: компенсация 1/150 × ставка ЦБ (ТК РФ ст. 236)."""
    data = dict(form_data)
    data["calculated_intro_section"] = ""
    data["calculated_violation_section"] = ""
    data["calculated_compensation_section"] = ""
    data["calculated_amount_section"] = ""
    data["calculated_demand_section"] = ""

    employer_name = str(data.get("employer_name") or "").strip()
    employer_inn = str(data.get("employer_inn") or "").strip()
    position = str(data.get("position") or "").strip()
    work_start = _ru_date(data.get("work_start"))
    work_end = _ru_date(data.get("work_end"))
    salary_owed_str = str(data.get("salary_owed") or "0")
    violation_type = str(data.get("violation_type") or "").strip()
    last_payment_date = _parse_date(data.get("last_payment_date"))

    try:
        salary_owed = Decimal(salary_owed_str)
    except Exception:
        salary_owed = Decimal("0")

    # Intro
    intro = "Между мной и индивидуальным предпринимателем"
    if employer_name:
        intro += f" {employer_name}"
    if employer_inn:
        intro += f" (ИНН {employer_inn})"
    intro += " сложились трудовые отношения"
    if position:
        intro += f" с фактическим выполнением работы в должности {position}"
    if work_start:
        intro += f" с {work_start}"
    if work_end:
        intro += f" по {work_end}"
    intro += "."
    data["calculated_intro_section"] = intro

    # Violation
    violation_map = {
        "no_contract": "При фактическом допущении к работе договор трудовой не был оформлен.",
        "salary_not_paid": "ИП задолжал заработную плату.",
        "dismissal": "ИП произвёл незаконное увольнение.",
        "no_vacation_pay": "ИП не выплатил отпускные при увольнении.",
    }
    data["calculated_violation_section"] = violation_map.get(
        violation_type,
        "ИП нарушил трудовое законодательство.",
    )

    # Compensation (similar to employer)
    if last_payment_date and salary_owed > 0:
        delay_days = max((date.today() - last_payment_date).days, 0)
        compensation = salary_owed * Decimal("1") / Decimal("150") * _get_cb_rate() / Decimal("100") * Decimal(delay_days)
        compensation = compensation.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        data["calculated_compensation"] = _fmt(compensation)
        total = salary_owed + compensation
        data["calculated_compensation_section"] = (
            f"Компенсация за задержку {delay_days} дней: "
            f"{_fmt(salary_owed)} руб. × 1/150 × {_get_cb_rate()}% × {delay_days} дней = "
            f"{_fmt(compensation)} руб. (ТК РФ ст. 236). "
            f"Итого к выплате: {_fmt(total)} руб."
        )
        data["calculated_amount_section"] = data["calculated_compensation_section"]
    else:
        data["calculated_amount_section"] = f"Сумма задолженности: {_fmt(salary_owed)} руб."

    data["calculated_demand_section"] = (
        f"На основании ТК РФ ст. 67.1 (де-факто трудовые отношения) и ст. 236 "
        f"(компенсация за задержку выплат) прошу выплатить мне задолженность "
        f"и компенсацию в течение трёх рабочих дней с даты получения претензии. "
        f"В противном случае буду обращаться в Трудовую инспекцию и в суд."
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
    "rental_deposit": calculate_rental_deposit,
    "court_order": calculate_court_order,
    "neighbor_flood": calculate_neighbor_flood,
    "ddu_defects": calculate_ddu_defects,
    "online_course": calculate_online_course,
    "tour_operator": calculate_tour_operator,
    "medical": calculate_medical,
    "marketplace": calculate_marketplace,
    "carsharing": calculate_carsharing,
    "bank": calculate_bank,
    "bank_block": calculate_bank_block,
    "utility": calculate_utility,
    "gibdd": calculate_gibdd,
    "debt_collector": calculate_debt_collector,
    "mfo": calculate_mfo,
    "gibdd_camera": calculate_gibdd_camera,
    "repair_apartment": calculate_repair_apartment,
    "online_shop_delivery": calculate_online_shop_delivery,
    "education_refund": calculate_education_refund,
    "university_admission": calculate_university_admission,
    "ip_employer": calculate_ip_employer,
}
