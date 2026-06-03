"""Tests for structured address composition (services/address_compose.py)."""
from app.services.address_compose import compose_contact_address, compose_store_address


def test_full_address():
    result = compose_contact_address({
        "address_city": "Москва",
        "address_street": "Пушкина",
        "address_house": "1",
        "address_building": "2",
        "address_structure": "3",
        "address_apartment": "5",
    })
    assert result == "г. Москва, ул. Пушкина, д. 1, корп. 2, стр. 3, кв. 5"


def test_required_only_skips_empty_parts():
    result = compose_contact_address({
        "address_city": "Казань",
        "address_street": "Баумана",
        "address_house": "10",
    })
    assert result == "г. Казань, ул. Баумана, д. 10"


def test_city_marker_not_duplicated():
    # Пользователь уже написал «г. Москва» — не должно стать «г. г. Москва».
    result = compose_contact_address({
        "address_city": "г. Москва",
        "address_street": "Пушкина",
        "address_house": "1",
    })
    assert result == "г. Москва, ул. Пушкина, д. 1"


def test_street_type_marker_preserved():
    # «пер. Александра Невского» — не превращаем в «ул. пер. …».
    result = compose_contact_address({
        "address_city": "Москва",
        "address_street": "пер. Александра Невского",
        "address_house": "4",
    })
    assert result == "г. Москва, пер. Александра Невского, д. 4"


def test_falls_back_to_legacy_contact_address():
    # Старая форма/заказ: подполей нет, есть готовый contact_address.
    result = compose_contact_address({"contact_address": "г. Москва, ул. Старая, д. 7"})
    assert result == "г. Москва, ул. Старая, д. 7"


def test_building_without_house():
    # «не у всех есть дом, но есть корпус» — корпус выводится без «д.».
    result = compose_contact_address({
        "address_city": "Москва",
        "address_building": "5",
    })
    assert result == "г. Москва, корп. 5"


def test_city_only():
    assert compose_contact_address({"address_city": "Норильск"}) == "г. Норильск"


def test_apartment_only_no_leading_comma():
    # Любая одиночная часть — без висячих запятых.
    assert compose_contact_address({"address_apartment": "12"}) == "кв. 12"


def test_village_with_house_no_street():
    # Село без улицы: «с. Бор» + дом, улица пропущена.
    result = compose_contact_address({
        "address_city": "с. Бор",
        "address_house": "3",
    })
    assert result == "с. Бор, д. 3"


def test_empty_returns_empty():
    assert compose_contact_address({}) == ""


def test_whitespace_only_subfields_fall_back():
    # Пробельные подполя не считаются заполненными.
    result = compose_contact_address({
        "address_city": "   ",
        "contact_address": "г. Сочи, ул. Морская, д. 2",
    })
    assert result == "г. Сочи, ул. Морская, д. 2"


# ── Адрес магазина (compose_store_address) ──────────────────────────────────


def test_store_full_physical_address():
    result = compose_store_address({
        "store_address_city": "Москва",
        "store_address_street": "Тверская",
        "store_address_house": "1",
        "store_address_building": "2",
        "store_address_structure": "3",
    })
    assert result == "г. Москва, ул. Тверская, д. 1, корп. 2, стр. 3"


def test_store_site_only():
    # Онлайн-магазин: заполнен только сайт.
    assert compose_store_address({"store_site": "www.mvideo.ru"}) == "www.mvideo.ru"


def test_store_address_and_site_combined():
    result = compose_store_address({
        "store_address_city": "Москва",
        "store_site": "www.mvideo.ru",
    })
    assert result == "г. Москва, сайт: www.mvideo.ru"


def test_store_no_apartment_field():
    # У магазина квартиры нет — address_apartment не учитывается.
    result = compose_store_address({
        "store_address_city": "Казань",
        "store_address_house": "10",
    })
    assert result == "г. Казань, д. 10"


def test_store_falls_back_to_legacy_store_address():
    # Старая форма/заказ: подполей нет, есть готовый store_address.
    result = compose_store_address({"store_address": "г. Москва, ул. Старая, д. 7"})
    assert result == "г. Москва, ул. Старая, д. 7"


def test_store_empty_returns_empty():
    assert compose_store_address({}) == ""
