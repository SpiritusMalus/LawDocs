"""Unit tests for services/calculators.py — deterministic math, no DB needed."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.calculators import (
    SITUATION_CALCULATORS,
    calculate_ddu_delay,
    calculate_ddu_termination,
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
