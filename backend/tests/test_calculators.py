"""Tests for deterministic calculators in app/services/calculators.py."""
import pytest

from app.services.calculators import (
    calculate_airline,
    calculate_court_order,
    calculate_education_refund,
    calculate_employer,
    calculate_gibdd_camera,
    calculate_ip_employer,
    calculate_mfo,
    calculate_online_shop_delivery,
    calculate_repair,
    calculate_repair_apartment,
    calculate_shop,
    calculate_university_admission,
)
from app.services.text_cleanup import fix_dashes


def _airline(violation="delay", delay_hours=0, ticket_price=0.0):
    return calculate_airline({
        "violation_type": violation,
        "delay_hours": str(delay_hours),
        "ticket_price": str(ticket_price),
        "flight_number": "SU100",
        "route": "Москва — Сочи",
        "flight_date": "2026-06-01",
        "airline": "Аэрофлот",
        "extra_expenses": "0",
        "received_compensation": "0",
    })


def _parse(value):
    return float(str(value).replace(" ", "").replace(" ", "").replace(",", "."))


# ст. 120 ВК: штраф = 25% базовой суммы (100 руб. по ст. 5 ФЗ-82), а НЕ реального
# МРОТ. Базовая ставка штрафа — 25 руб./час.
BASE_SUM = 100
PER_HOUR = round(BASE_SUM * 0.25, 2)  # 25 руб./час


def test_airline_no_delay_skips_calc():
    result = _airline("delay", delay_hours=0, ticket_price=10000)
    assert result.get("calculated_delay_comp") is None


def test_airline_delay_formula_basic():
    hours = 5
    ticket = 12000.0
    result = _airline("delay", delay_hours=hours, ticket_price=ticket)
    # 25 руб. × 5 ч. = 125 руб. (потолок 50% билета = 6000 руб. не достигнут)
    expected = min(round(PER_HOUR * hours, 2), round(ticket * 0.5, 2))
    assert _parse(result["calculated_delay_comp"]) == expected == 125.0


def test_airline_delay_cap_applied():
    # Очень долгая просрочка: 25 руб./ч × 300 ч = 7500 руб., но потолок 50% билета.
    hours = 300
    ticket = 1000.0
    result = _airline("delay", delay_hours=hours, ticket_price=ticket)
    cap = round(ticket * 0.5, 2)
    assert _parse(result["calculated_delay_comp"]) == cap == 500.0


def test_airline_delay_no_ticket_skips_calc():
    result = _airline("delay", delay_hours=5, ticket_price=0)
    assert result.get("calculated_delay_comp") is None


def test_airline_delay_uses_statutory_base_not_real_mrot():
    """Регресс-гард: штраф считается от базовой суммы 100 руб., а не реального МРОТ.

    Раньше подставлялся settings.MROT (~27 000 ₽), завышая штраф в ~270 раз."""
    hours = 4
    result = _airline("delay", delay_hours=hours, ticket_price=1_000_000.0)
    # Лимит билета (500 000) огромен, поэтому связывает именно базовая ставка.
    assert _parse(result["calculated_delay_comp"]) == round(PER_HOUR * hours, 2) == 100.0


def test_airline_delay_no_fabricated_fine():
    """Не выдумываем второй «штраф 50% от билета»: в требовании только ст.120 ВК."""
    result = _airline("delay", delay_hours=5, ticket_price=12000.0)
    assert "calculated_fine" not in result
    # Итог = только компенсация по ст.120, без добавочного 50% билета.
    assert _parse(result["calculated_total"]) == _parse(result["calculated_delay_comp"]) == 125.0
    assert "ст. 28" not in result["calculated_amount_section"]


def test_airline_cancellation_no_delay_comp():
    result = _airline("cancellation", ticket_price=10000)
    assert result.get("calculated_delay_comp") is None


def test_shop_penalty_basic():
    from datetime import date, timedelta
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    result = calculate_shop({
        "problem_type": "return_refused",
        "product_name": "Телефон",
        "product_price": "10000",
        "appeal_date": ten_days_ago,
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty == pytest.approx(1000.0)


def test_shop_penalty_cap():
    from datetime import date, timedelta
    long_ago = (date.today() - timedelta(days=200)).isoformat()
    result = calculate_shop({
        "problem_type": "return_refused",
        "product_name": "Телефон",
        "product_price": "1000",
        "appeal_date": long_ago,
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty <= 1000.0


def test_employer_compensation_basic():
    from datetime import date, timedelta
    thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
    result = calculate_employer({
        "violation_type": "salary",
        "debt_amount": "100000",
        "last_payment_date": thirty_days_ago,
        "company_name": "ООО Ромашка",
    })
    comp = _parse(result.get("calculated_compensation", "0"))
    expected = round(100000 * (1 / 150) * (21 / 100) * 30, 2)
    assert comp == pytest.approx(expected, abs=1.0)


def test_employer_no_payment_date_no_comp():
    result = calculate_employer({
        "violation_type": "salary",
        "debt_amount": "50000",
        "company_name": "ООО Тест",
    })
    # без last_payment_date — компенсация не вычисляется, только долг
    assert result.get("calculated_compensation") == ""


def test_repair_penalty_basic():
    from datetime import date, timedelta
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    result = calculate_repair({
        "work_type": "Ремонт ноутбука",
        "work_price": "5000",
        "defect_discovery_date": ten_days_ago,
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty == pytest.approx(1500.0)


def test_repair_penalty_cap():
    from datetime import date, timedelta
    long_ago = (date.today() - timedelta(days=200)).isoformat()
    result = calculate_repair({
        "work_type": "Ремонт ноутбука",
        "work_price": "1000",
        "defect_discovery_date": long_ago,
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty <= 1000.0


def test_mfo_excess_rate_computed():
    from datetime import date, timedelta
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    result = calculate_mfo({
        "mfo_name": "МФО Тест",
        "loan_amount": "10000",
        "loan_date": ten_days_ago,
        "daily_rate": "1.5",
        "violation_type": "illegal_rate",
    })
    assert "calculated_amount_section" in result
    assert result["calculated_amount_section"] != ""


def test_mfo_no_violation_no_calc():
    result = calculate_mfo({
        "mfo_name": "МФО Тест",
        "loan_amount": "10000",
        "loan_date": "2026-05-01",
        "daily_rate": "0.8",
        "violation_type": "illegal_rate",
    })
    assert "calculated_amount_section" in result


def test_gibdd_camera_deadline_10_days():
    from datetime import date, timedelta
    five_days_ago = (date.today() - timedelta(days=5)).isoformat()
    result = calculate_gibdd_camera({
        "fine_date": five_days_ago,
        "fine_amount": "500",
        "fine_number": "1234",
        "vehicle_number": "А123БВ77",
        "violation_type": "wrong_owner",
    })
    assert "calculated_deadline_section" in result
    assert result["calculated_deadline_section"] != ""


def test_repair_apartment_penalty_3pct():
    from datetime import date, timedelta
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    result = calculate_repair_apartment({
        "contractor_name": "Иван Петров",
        "contract_date": "2026-04-01",
        "contract_amount": "100000",
        "defect_discovery_date": ten_days_ago,
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty == pytest.approx(30000.0)


def test_repair_apartment_penalty_capped():
    from datetime import date, timedelta
    long_ago = (date.today() - timedelta(days=200)).isoformat()
    result = calculate_repair_apartment({
        "contractor_name": "Иван Петров",
        "contract_date": "2026-04-01",
        "contract_amount": "100000",
        "defect_discovery_date": long_ago,
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty <= 100000.0


def test_online_shop_not_delivered_0_5pct():
    from datetime import date, timedelta
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    result = calculate_online_shop_delivery({
        "shop_name": "example.ru",
        "order_date": ten_days_ago,
        "order_amount": "10000",
        "order_number": "12345",
        "problem_type": "not_delivered",
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty == pytest.approx(500.0)


def test_online_shop_wrong_item_1pct():
    from datetime import date, timedelta
    ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
    result = calculate_online_shop_delivery({
        "shop_name": "example.ru",
        "order_date": ten_days_ago,
        "order_amount": "10000",
        "order_number": "12345",
        "problem_type": "wrong_item",
    })
    penalty = _parse(result.get("calculated_penalty", "0"))
    assert penalty == pytest.approx(1000.0)


def test_education_refund_proportional():
    result = calculate_education_refund({
        "school_name": "Школа",
        "course_name": "Курс",
        "paid_amount": "50000",
        "total_classes": "20",
        "attended_classes": "5",
    })
    # 50000 / 20 × 15 = 37500 (формат с разделителем тысяч: «37 500»)
    assert "37500" in result["calculated_amount_section"].replace(" ", "")


def test_education_refund_zero_classes_full_refund():
    result = calculate_education_refund({
        "school_name": "Школа",
        "course_name": "Курс",
        "paid_amount": "50000",
        "total_classes": "0",
        "attended_classes": "0",
    })
    # total_classes = 0 → full refund
    assert "50000" in result["calculated_amount_section"].replace(" ", "")


def test_university_admission_formats_correctly():
    result = calculate_university_admission({
        "university_name": "МГУ",
        "specialty": "Математика",
        "violation_type": "not_admitted",
        "application_date": "2026-05-01",
    })
    assert "calculated_intro_section" in result
    assert result["calculated_intro_section"] != ""
    assert "calculated_demand_section" in result
    assert result["calculated_demand_section"] != ""


# ── Регрессии качества генерации (BUG 3/4/5) ──────────────────

_ALL_SECTION_KEYS = (
    "calculated_intro_section",
    "calculated_violation_section",
    "calculated_amount_section",
    "calculated_demand_section",
    "calculated_compensation_section",
    "calculated_deadline_section",
)


def _all_text(result: dict) -> str:
    return " ".join(str(result.get(k, "")) for k in _ALL_SECTION_KEYS)


def test_gibdd_camera_maps_violation_to_russian():
    # BUG 5: сырое enum-значение не должно попадать в текст
    result = calculate_gibdd_camera({
        "fine_date": "2026-04-10",
        "fine_amount": "500",
        "fine_number": "1234",
        "vehicle_number": "А123БВ77",
        "violation_type": "not_driving",
    })
    intro = result["calculated_intro_section"]
    assert "not_driving" not in intro
    assert "не управлял" in intro


def test_gibdd_camera_unknown_violation_no_raw_leak():
    result = calculate_gibdd_camera({
        "fine_date": "2026-04-10",
        "fine_amount": "500",
        "violation_type": "other",
    })
    assert "other" not in result["calculated_intro_section"].split()


def test_court_order_empty_fields_no_double_dash():
    # BUG 3: пустые поля не должны давать соседние тире «— —»
    result = calculate_court_order({
        "case_number": "",
        "order_date": "",
        "creditor_name": "",
        "debt_amount": "0",
        "objection_reason": "dispute_amount",
    })
    text = _all_text(result)
    assert "— —" not in text
    assert "№ —" not in text
    assert "№ ," not in text  # пустой номер не оставляет висячего «№»


def test_no_gendered_suffix_in_calculators():
    # BUG 4: ни в одном выводе не должно быть «(-а)»
    samples = [
        calculate_gibdd_camera({"fine_date": "2026-04-10", "fine_amount": "500", "violation_type": "wrong_owner"}),
        calculate_mfo({"mfo_name": "ООО МФК", "loan_amount": "15000", "loan_date": "2026-03-01", "daily_rate": "2.0", "violation_type": "illegal_rate"}),
        calculate_education_refund({"school_name": "Школа", "course_name": "Курс", "paid_amount": "90000", "total_classes": "60", "attended_classes": "12", "refund_reason": "quality"}),
        calculate_university_admission({"university_name": "МГУ", "specialty": "Математика", "violation_type": "not_admitted", "application_date": "2026-05-01"}),
        calculate_ip_employer({"employer_name": "ИП Петров", "employer_inn": "7727000001", "position": "продавец", "work_start": "2025-09-01", "work_end": "2026-04-30", "salary_owed": "78000", "last_payment_date": "2026-03-31", "violation_type": "salary_not_paid"}),
        calculate_shop({"product_name": "Товар", "product_price": "10000", "problem_type": "defect", "purchase_date": "2026-01-01", "appeal_date": "2026-02-01", "demand": "refund"}),
    ]
    for r in samples:
        assert "(-а)" not in _all_text(r), f"gendered form leaked: {_all_text(r)!r}"


def test_shop_penalty_with_ru_date_format():
    # Регресс: фронт шлёт дату в формате «дд.мм.гггг». Раньше _parse_date умел
    # только ISO → дата молча не парсилась и неустойка не считалась.
    from datetime import date, timedelta

    ten_days_ago = (date.today() - timedelta(days=10)).strftime("%d.%m.%Y")
    result = calculate_shop({
        "product_name": "Товар",
        "product_price": "10000",
        "problem_type": "defect",
        "purchase_date": "01.01.2026",
        "appeal_date": ten_days_ago,
        "demand": "refund",
    })
    assert result.get("calculated_penalty_days") == "10"
    assert result.get("calculated_penalty")  # сумма посчитана, а не пропущена
    assert "10 дней" in result["calculated_penalty_section"]


def test_parse_date_accepts_both_formats():
    from datetime import date

    from app.services.calculators import _parse_date

    assert _parse_date("15.03.2026") == date(2026, 3, 15)
    assert _parse_date("2026-03-15") == date(2026, 3, 15)
    assert _parse_date("не дата") is None
    assert _parse_date("") is None
    assert _parse_date(None) is None


def test_fix_dashes_collapses_adjacent_em():
    assert fix_dashes("текст — — текст") == "текст — текст"
    assert fix_dashes("№ — от — —") == "№ — от —"
    # регресс: дефисы по-прежнему превращаются в длинное тире
    assert fix_dashes("a--b") == "a—b"
    # одиночное тире-разделитель не трогаем
    assert fix_dashes("взыскатель — Иванов") == "взыскатель — Иванов"
