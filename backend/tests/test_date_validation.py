"""Tests for declarative date validation (app/situations/validate.py)
and its wiring into OrderInitRequest."""
from datetime import date, timedelta

import pytest

from app.schemas.order import OrderInitRequest
from app.situations.registry import registry
from app.situations.validate import validate_dates


def _shop(**overrides) -> dict:
    data = {
        "store_name": "М.Видео",
        "product_name": "Телефон",
        "product_price": "10000",
        "problem_type": "defect",
        "problem_desc": "Сломался",
        "demand": "refund",
        "purchase_date": "01.01.2026",
        "appeal_date": "01.02.2026",
        "address_city": "Москва",  # адрес обязателен на уровне схемы (validate_address)
    }
    data.update(overrides)
    return data


def test_valid_shop_dates_pass():
    config = registry.get("shop")
    validate_dates(config, _shop())  # не должно бросить


def test_appeal_before_purchase_rejected():
    config = registry.get("shop")
    with pytest.raises(ValueError, match="не может быть раньше"):
        validate_dates(config, _shop(purchase_date="01.02.2026", appeal_date="01.01.2026"))


def test_future_purchase_date_rejected():
    config = registry.get("shop")
    future = (date.today() + timedelta(days=5)).strftime("%d.%m.%Y")
    with pytest.raises(ValueError, match="в будущем"):
        validate_dates(config, _shop(purchase_date=future))


def test_bad_date_format_rejected():
    config = registry.get("shop")
    with pytest.raises(ValueError, match="неверная дата"):
        validate_dates(config, _shop(purchase_date="32.13.2026"))


def test_empty_optional_date_skipped():
    config = registry.get("shop")
    validate_dates(config, _shop(appeal_date=""))  # пустая необязательная — ок


def test_iso_format_also_accepted():
    config = registry.get("shop")
    validate_dates(config, _shop(purchase_date="2026-01-01", appeal_date="2026-02-01"))


def test_ddu_delay_chain():
    config = registry.get("ddu_delay")
    base = {
        "contract_date": "01.01.2024",
        "planned_transfer_date": "01.01.2025",
        "actual_transfer_date": "01.06.2025",
    }
    validate_dates(config, base)  # упорядочено — ок
    with pytest.raises(ValueError, match="не может быть раньше"):
        validate_dates(config, {**base, "actual_transfer_date": "01.01.2024"})


def test_order_init_request_rejects_contradictory_dates():
    # model_validator должен поднять ошибку валидации на уровне схемы
    with pytest.raises(ValueError):
        OrderInitRequest(
            email="user@example.com",
            situation_id="shop",
            form_data=_shop(purchase_date="01.02.2026", appeal_date="01.01.2026"),
        )


def test_order_init_request_accepts_valid_dates():
    req = OrderInitRequest(
        email="user@example.com",
        situation_id="shop",
        form_data=_shop(),
    )
    assert req.situation_id == "shop"
