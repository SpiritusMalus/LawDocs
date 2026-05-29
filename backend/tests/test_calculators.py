"""Tests for deterministic calculators in app/services/calculators.py."""
from unittest.mock import patch

import pytest

from app.services.calculators import (
    calculate_airline,
    calculate_employer,
    calculate_repair,
    calculate_shop,
)


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


MROT = 27093
PER_HOUR = round(MROT * 0.25, 2)


def test_airline_no_delay_skips_calc():
    result = _airline("delay", delay_hours=0, ticket_price=10000)
    assert result.get("calculated_delay_comp") is None


def test_airline_delay_formula_basic():
    hours = 2
    ticket = 1_000_000.0
    result = _airline("delay", delay_hours=hours, ticket_price=ticket)
    expected = min(round(PER_HOUR * hours, 2), round(ticket * 0.5, 2))
    assert _parse(result["calculated_delay_comp"]) == expected


def test_airline_delay_cap_applied():
    hours = 100
    ticket = 500.0
    result = _airline("delay", delay_hours=hours, ticket_price=ticket)
    cap = round(ticket * 0.5, 2)
    assert _parse(result["calculated_delay_comp"]) <= cap


def test_airline_delay_no_ticket_skips_calc():
    result = _airline("delay", delay_hours=5, ticket_price=0)
    assert result.get("calculated_delay_comp") is None


def test_airline_delay_uses_settings_mrot():
    custom_mrot = 30000
    with patch("app.services.calculators.settings") as mock_settings:
        mock_settings.MROT = custom_mrot
        result = _airline("delay", delay_hours=1, ticket_price=1_000_000.0)
    expected = round(custom_mrot * 0.25, 2)
    assert _parse(result["calculated_delay_comp"]) == expected


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
