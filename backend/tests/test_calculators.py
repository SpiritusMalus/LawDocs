"""Unit tests for services/calculators.py — deterministic math, no DB needed."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.calculators import (
    SITUATION_CALCULATORS,
    calculate_auto_repair,
    calculate_ddu_delay,
    calculate_ddu_termination,
    calculate_shop,
)


# ---------------------------------------------------------------------------
# calculate_ddu_delay
# ---------------------------------------------------------------------------

class TestCalculateDduDelay:
    def _base(self, **overrides) -> dict:
        data = {
            "planned_transfer_date": "2026-01-01",
            "actual_transfer_date": "2026-04-11",  # 100 days later
            "contract_price": "3000000",
            "cb_rate": "16.0",
        }
        data.update(overrides)
        return data

    def test_correct_delay_days(self):
        result = calculate_ddu_delay(self._base())
        assert result["calculated_delay_days"] == "100"

    def test_correct_neustoyka(self):
        # 3_000_000 × 16 / 100 / 150 × 100 = 320_000.00
        result = calculate_ddu_delay(self._base())
        assert result["calculated_neustoyka"] == "320000.00"

    def test_no_delay_when_actual_before_planned(self):
        result = calculate_ddu_delay(self._base(
            planned_transfer_date="2026-06-01",
            actual_transfer_date="2026-04-01",
        ))
        assert result["calculated_delay_days"] == "0"
        assert result["calculated_neustoyka"] == "0.00"

    def test_missing_planned_date_returns_unchanged(self):
        data = self._base()
        del data["planned_transfer_date"]
        result = calculate_ddu_delay(data)
        assert "calculated_delay_days" not in result
        assert "calculated_neustoyka" not in result

    def test_missing_price_returns_unchanged(self):
        data = self._base()
        del data["contract_price"]
        result = calculate_ddu_delay(data)
        assert "calculated_neustoyka" not in result

    def test_invalid_date_format_returns_unchanged(self):
        result = calculate_ddu_delay(self._base(planned_transfer_date="01.01.2026"))
        assert "calculated_delay_days" not in result

    def test_does_not_mutate_input(self):
        original = self._base()
        copy = dict(original)
        calculate_ddu_delay(original)
        assert original == copy

    def test_actual_date_falls_back_to_today(self):
        data = {
            "planned_transfer_date": "2025-01-01",
            "contract_price": "1000000",
            "cb_rate": "16.0",
        }
        today = date.today()
        expected_days = max((today - date(2025, 1, 1)).days, 0)
        result = calculate_ddu_delay(data)
        assert result["calculated_delay_days"] == str(expected_days)


# ---------------------------------------------------------------------------
# calculate_ddu_termination
# ---------------------------------------------------------------------------

_FIXED_TODAY = date(2026, 5, 18)
_PAYMENT_DATE = date(2026, 2, 7)  # 100 days before _FIXED_TODAY
_DAYS_USED = (_FIXED_TODAY - _PAYMENT_DATE).days  # == 100


class TestCalculateDduTermination:
    def _base(self, **overrides) -> dict:
        data = {
            "payment_date": _PAYMENT_DATE.isoformat(),
            "contract_price": "2000000",
            "cb_rate": "16.0",
        }
        data.update(overrides)
        return data

    def test_correct_days_used(self):
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _FIXED_TODAY
            mock_date.fromisoformat = date.fromisoformat
            result = calculate_ddu_termination(self._base())
        assert result["calculated_days_used"] == str(_DAYS_USED)

    def test_correct_interest(self):
        # 2_000_000 × 16 / 100 / 150 × 100 = 213_333.33
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _FIXED_TODAY
            mock_date.fromisoformat = date.fromisoformat
            result = calculate_ddu_termination(self._base())
        assert result["calculated_interest"] == "213333.33"

    def test_correct_total_return(self):
        # 2_000_000 + 213_333.33 = 2_213_333.33
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _FIXED_TODAY
            mock_date.fromisoformat = date.fromisoformat
            result = calculate_ddu_termination(self._base())
        assert result["calculated_total_return"] == "2213333.33"

    def test_missing_payment_date_returns_unchanged(self):
        data = self._base()
        del data["payment_date"]
        result = calculate_ddu_termination(data)
        assert "calculated_days_used" not in result
        assert "calculated_total_return" not in result

    def test_missing_price_returns_unchanged(self):
        data = self._base()
        del data["contract_price"]
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _FIXED_TODAY
            mock_date.fromisoformat = date.fromisoformat
            result = calculate_ddu_termination(data)
        assert "calculated_total_return" not in result

    def test_does_not_mutate_input(self):
        original = self._base()
        copy = dict(original)
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _FIXED_TODAY
            mock_date.fromisoformat = date.fromisoformat
            calculate_ddu_termination(original)
        assert original == copy


# ---------------------------------------------------------------------------
# SITUATION_CALCULATORS registry
# ---------------------------------------------------------------------------

def test_registry_has_ddu_delay():
    assert "ddu_delay" in SITUATION_CALCULATORS
    assert SITUATION_CALCULATORS["ddu_delay"] is calculate_ddu_delay


def test_registry_has_ddu_termination():
    assert "ddu_termination" in SITUATION_CALCULATORS
    assert SITUATION_CALCULATORS["ddu_termination"] is calculate_ddu_termination


# ---------------------------------------------------------------------------
# calculate_shop
# ---------------------------------------------------------------------------

_SHOP_TODAY = date(2026, 5, 24)
_SHOP_START = date(2026, 4, 14)   # 40 days before _SHOP_TODAY
_SHOP_DAYS = (_SHOP_TODAY - _SHOP_START).days  # == 40


class TestCalculateShop:
    def _base(self, **overrides) -> dict:
        data = {
            "product_price": "10000",
            "appeal_date": _SHOP_START.isoformat(),
        }
        data.update(overrides)
        return data

    def _run(self, data):
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _SHOP_TODAY
            mock_date.fromisoformat = date.fromisoformat
            return calculate_shop(data)

    def test_correct_penalty_days(self):
        result = self._run(self._base())
        assert result["calculated_penalty_days"] == str(_SHOP_DAYS)

    def test_correct_penalty(self):
        # 10000 × 1% × 40 = 4000.00
        result = self._run(self._base())
        assert result["calculated_penalty"] == "4000.00"

    def test_penalty_capped_at_product_price(self):
        # 10000 × 1% × 200 = 20000 → capped at 10000.00
        data = self._base(appeal_date=date(2026, 1, 1).isoformat())
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = date(2026, 10, 1)
            mock_date.fromisoformat = date.fromisoformat
            result = calculate_shop(data)
        assert Decimal(result["calculated_penalty"]) == Decimal("10000.00")

    def test_penalty_start_date_takes_priority_over_appeal_date(self):
        data = self._base(
            appeal_date=date(2026, 1, 1).isoformat(),  # old → many days
            penalty_start_date=_SHOP_START.isoformat(),  # 40 days
        )
        result = self._run(data)
        assert result["calculated_penalty_days"] == str(_SHOP_DAYS)

    def test_no_date_returns_empty_section(self):
        data = {"product_price": "10000"}
        result = calculate_shop(data)
        assert result["calculated_penalty_section"] == ""
        assert "calculated_penalty_days" not in result
        assert "calculated_penalty" not in result

    def test_missing_price_returns_empty_section(self):
        data = {"appeal_date": _SHOP_START.isoformat()}
        result = self._run(data)
        assert result["calculated_penalty_section"] == ""

    def test_section_contains_days_and_amount(self):
        result = self._run(self._base())
        assert str(_SHOP_DAYS) in result["calculated_penalty_section"]
        assert "4000.00" in result["calculated_penalty_section"]

    def test_does_not_mutate_input(self):
        original = self._base()
        copy = dict(original)
        self._run(original)
        assert original == copy


def test_registry_has_shop():
    assert "shop" in SITUATION_CALCULATORS
    assert SITUATION_CALCULATORS["shop"] is calculate_shop


# ---------------------------------------------------------------------------
# calculate_auto_repair
# ---------------------------------------------------------------------------

_AR_TODAY = date(2026, 5, 24)
_AR_PLANNED = date(2026, 5, 4)   # 20 days before _AR_TODAY
_AR_DAYS = (_AR_TODAY - _AR_PLANNED).days  # == 20


class TestCalculateAutoRepairDelay:
    def _base(self, **overrides) -> dict:
        data = {
            "violation_type": "delay",
            "work_price": "50000",
            "planned_date": _AR_PLANNED.isoformat(),
        }
        data.update(overrides)
        return data

    def _run(self, data):
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = _AR_TODAY
            mock_date.fromisoformat = date.fromisoformat
            return calculate_auto_repair(data)

    def test_correct_delay_days(self):
        result = self._run(self._base())
        assert result["calculated_delay_days"] == str(_AR_DAYS)

    def test_correct_penalty_3pct(self):
        # 50000 × 3% × 20 = 30000.00
        result = self._run(self._base())
        assert result["calculated_penalty"] == "30000.00"

    def test_penalty_capped_at_work_price(self):
        data = self._base(planned_date=date(2026, 1, 1).isoformat())
        with patch("app.services.calculators.date") as mock_date:
            mock_date.today.return_value = date(2026, 10, 1)
            mock_date.fromisoformat = date.fromisoformat
            result = calculate_auto_repair(data)
        assert Decimal(result["calculated_penalty"]) == Decimal("50000.00")

    def test_no_planned_date_returns_empty_section(self):
        data = {"violation_type": "delay", "work_price": "50000"}
        result = self._run(data)
        assert result["calculated_penalty_section"] == ""

    def test_section_contains_days_and_amount(self):
        result = self._run(self._base())
        assert str(_AR_DAYS) in result["calculated_penalty_section"]
        assert "30000.00" in result["calculated_penalty_section"]


class TestCalculateAutoRepairOvercharge:
    def _base(self, **overrides) -> dict:
        data = {
            "violation_type": "overcharge",
            "work_price": "45000",
            "agreed_price": "30000",
        }
        data.update(overrides)
        return data

    def test_correct_overcharge_diff(self):
        result = calculate_auto_repair(self._base())
        assert result["calculated_overcharge_diff"] == "15000.00"

    def test_overcharge_section_contains_amounts(self):
        result = calculate_auto_repair(self._base())
        assert "15000.00" in result["calculated_overcharge_section"]
        assert "45000.00" in result["calculated_overcharge_section"]
        assert "30000.00" in result["calculated_overcharge_section"]

    def test_missing_agreed_price_returns_empty_section(self):
        data = {"violation_type": "overcharge", "work_price": "45000"}
        result = calculate_auto_repair(data)
        assert result["calculated_overcharge_section"] == ""

    def test_penalty_section_empty_for_overcharge(self):
        result = calculate_auto_repair(self._base())
        assert result["calculated_penalty_section"] == ""


class TestCalculateAutoRepairBadQuality:
    def test_penalty_section_empty(self):
        data = {"violation_type": "bad_quality", "work_price": "50000"}
        result = calculate_auto_repair(data)
        assert result["calculated_penalty_section"] == ""

    def test_overcharge_section_empty(self):
        data = {"violation_type": "bad_quality", "work_price": "50000"}
        result = calculate_auto_repair(data)
        assert result["calculated_overcharge_section"] == ""


def test_auto_repair_does_not_mutate_input():
    original = {"violation_type": "delay", "work_price": "50000", "planned_date": _AR_PLANNED.isoformat()}
    copy = dict(original)
    with patch("app.services.calculators.date") as mock_date:
        mock_date.today.return_value = _AR_TODAY
        mock_date.fromisoformat = date.fromisoformat
        calculate_auto_repair(original)
    assert original == copy


def test_registry_has_auto_repair():
    assert "auto_repair" in SITUATION_CALCULATORS
    assert SITUATION_CALCULATORS["auto_repair"] is calculate_auto_repair
