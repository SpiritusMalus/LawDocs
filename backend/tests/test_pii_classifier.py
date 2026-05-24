"""Тесты границы приватности: классификация полей и фильтрация для LLM."""

import pytest

from app.services.pii_classifier import (
    FieldClass,
    classify_field,
    is_safe_for_llm,
    split_for_llm,
)


@pytest.mark.parametrize("field_id", [
    "full_name", "phone", "email", "contact_address", "apartment_address",
    "company_name", "company_inn", "director_name", "bank_name", "store_name",
    "contract_number", "policy_number", "amount", "product_price", "debt_amount",
    "purchase_date", "incident_date", "position",
])
def test_pii_fields_are_sensitive(field_id):
    assert classify_field(field_id) is FieldClass.SENSITIVE
    assert is_safe_for_llm(field_id) is False


@pytest.mark.parametrize("field_id", [
    "problem_desc", "store_response", "additional_desc", "incident_desc", "demand",
])
def test_text_fields_are_safe(field_id):
    assert classify_field(field_id) is FieldClass.TEXT
    assert is_safe_for_llm(field_id) is True


@pytest.mark.parametrize("field_id", [
    "situation_id", "problem_type", "violation_type", "incident_type",
    "platform", "platform_other", "policy_type",
])
def test_routing_fields_are_safe(field_id):
    assert classify_field(field_id) is FieldClass.ROUTING
    assert is_safe_for_llm(field_id) is True


def test_unknown_field_defaults_to_sensitive():
    """Deny by default — забытое в классификаторе поле не должно утечь в LLM."""
    assert classify_field("some_brand_new_field") is FieldClass.SENSITIVE
    assert is_safe_for_llm("some_brand_new_field") is False


def test_split_for_llm_keeps_pii_out():
    form_data = {
        "full_name": "Иванов Иван Иванович",
        "phone": "+79991234567",
        "contact_address": "г. Москва, ул. Пушкина, д.1",
        "product_price": "35000",
        "store_name": "DNS",
        "problem_desc": "Телефон сломался через неделю",
        "problem_type": "defect",
        "demand": "refund",
    }
    safe, sensitive = split_for_llm(form_data)

    # В safe — только TEXT/ROUTING
    assert set(safe) == {"problem_desc", "problem_type", "demand"}
    # Все ПДн — в sensitive
    assert set(sensitive) == {
        "full_name", "phone", "contact_address", "product_price", "store_name",
    }
    # Никакое значение ПДн не попало в safe-словарь
    for value in ("Иванов", "79991234567", "Пушкина", "35000", "DNS"):
        assert all(value not in str(v) for v in safe.values())


def test_split_preserves_all_keys():
    form_data = {"full_name": "X", "problem_desc": "Y", "platform": "wb"}
    safe, sensitive = split_for_llm(form_data)
    assert set(safe) | set(sensitive) == set(form_data)


# --- Поведение LLM-пайплайна (граница приватности в промпте/выходе) ---

def test_user_prompt_excludes_pii():
    """В промпт GigaChat не должны попадать имена, адреса, телефоны, суммы."""
    from app.services.llm import _build_user_prompt

    form_data = {
        "full_name": "Иванов Иван",
        "phone": "+79991234567",
        "contact_address": "ул. Пушкина, 1",
        "product_price": "35000",
        "problem_desc": "товар сломался",
        "problem_type": "defect",
    }
    prompt = _build_user_prompt("shop", form_data)

    assert "товар сломался" in prompt          # TEXT — должно быть
    assert "defect" in prompt                  # ROUTING — должно быть
    for pii in ("Иванов", "79991234567", "Пушкина", "35000"):
        assert pii not in prompt               # ПДн — не должно быть


def test_post_substitute_fills_placeholders_in_output():
    """ПДн подставляются в готовый текст документа через [field]-метки."""
    from app.services.llm import _post_substitute_output

    output = "От: [full_name], [contact_address], [phone]\nПРЕТЕНЗИЯ\nв магазин [store_name]"
    form_data = {
        "full_name": "Иванов Иван Иванович",
        "contact_address": "г. Москва, ул. Пушкина, д.1",
        "phone": "+79991234567",
        "store_name": "DNS",
    }
    result = _post_substitute_output(output, form_data)

    assert "[full_name]" not in result
    assert "Иванов Иван Иванович" in result
    assert "г. Москва, ул. Пушкина, д.1" in result
    assert "DNS" in result


def test_post_substitute_leaves_unknown_markers_intact():
    """Неизвестная метка остаётся как есть (не падаем, не выдумываем)."""
    from app.services.llm import _post_substitute_output

    result = _post_substitute_output("сумма: [calculated_total]", {"full_name": "X"})
    assert result == "сумма: [calculated_total]"
