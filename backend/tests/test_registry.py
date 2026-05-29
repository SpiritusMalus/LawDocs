"""Tests for the situation registry."""
import pytest
from app.situations.registry import registry, CONTACT_STEP

EXPECTED_IDS = {
    "shop", "marketplace", "bank", "bank_block", "employer", "insurance",
    "utility", "airline", "court_order", "gibdd", "rental_deposit",
    "tour_operator", "online_course", "neighbor_flood", "repair", "telecom",
    "medical", "ddu_delay", "ddu_defects", "ddu_termination", "dtp_osago",
    "auto_repair", "debt_collector", "carsharing", "gym_refund",
    "mfo", "gibdd_camera", "repair_apartment", "online_shop_delivery",
    "education_refund", "university_admission", "ip_employer",
}


def test_registry_loads_all_situations():
    assert EXPECTED_IDS <= registry.ids()


def test_registry_len():
    assert len(registry) == 32


def test_unknown_situation_returns_none():
    assert registry.get("unknown_situation") is None


def test_known_situation_returns_config():
    config = registry.get("shop")
    assert config is not None
    assert config.id == "shop"
    assert config.category == "consumer"


@pytest.mark.parametrize("situation_id", sorted(EXPECTED_IDS))
def test_each_situation_has_required_fields(situation_id: str):
    config = registry.get(situation_id)
    assert config is not None
    assert config.id
    assert config.title
    assert config.blurb
    assert config.system_prompt
    assert len(config.wizard_steps) >= 2


@pytest.mark.parametrize("situation_id", sorted(EXPECTED_IDS))
def test_contact_step_appended(situation_id: str):
    config = registry.get(situation_id)
    assert config is not None
    last_step = config.wizard_steps[-1]
    assert last_step.title == CONTACT_STEP.title
    contact_field_ids = {f.id for f in last_step.fields}
    assert "full_name" in contact_field_ids
    assert "email" in contact_field_ids
    assert "phone" in contact_field_ids


@pytest.mark.parametrize("situation_id", sorted(EXPECTED_IDS))
def test_base_rules_in_system_prompt(situation_id: str):
    config = registry.get(situation_id)
    assert config is not None
    assert "Официально-деловой стиль" in config.system_prompt
    assert "Верни ТОЛЬКО текст документа" in config.system_prompt


def test_shop_has_store_response_field():
    config = registry.get("shop")
    assert config is not None
    all_fields = [f for step in config.wizard_steps for f in step.fields]
    field_ids = {f.id for f in all_fields}
    assert "store_response" in field_ids
    assert "appeal_date" in field_ids


def test_employer_has_calculation_fields():
    config = registry.get("employer")
    assert config is not None
    all_fields = [f for step in config.wizard_steps for f in step.fields]
    field_ids = {f.id for f in all_fields}
    assert "debt_amount" in field_ids
    assert "last_payment_date" in field_ids


def test_insurance_has_damage_fields():
    config = registry.get("insurance")
    assert config is not None
    all_fields = [f for step in config.wizard_steps for f in step.fields]
    field_ids = {f.id for f in all_fields}
    assert "actual_damage" in field_ids
    assert "paid_amount" in field_ids
    assert "overdue_days" in field_ids


def test_airline_has_calculation_fields():
    config = registry.get("airline")
    assert config is not None
    all_fields = [f for step in config.wizard_steps for f in step.fields]
    field_ids = {f.id for f in all_fields}
    assert "delay_hours" in field_ids
    assert "ticket_price" in field_ids
    assert "extra_expenses" in field_ids


def test_all_radio_fields_have_options():
    for config in registry.all():
        for step in config.wizard_steps:
            for field in step.fields:
                if field.type == "radio":
                    assert field.options, (
                        f"Radio field '{field.id}' in '{config.id}' has no options"
                    )


def test_all_required_fields_have_labels():
    for config in registry.all():
        for step in config.wizard_steps:
            for field in step.fields:
                if field.required:
                    assert field.label, (
                        f"Required field '{field.id}' in '{config.id}' has no label"
                    )


def _all_legal_refs():
    """Все legal_refs (включая ветки) как (situation_id, law, url)."""
    for config in registry.all():
        refs = list(config.legal_refs)
        for branch in config.legal_refs_by_branch.values():
            refs += branch
        for ref in refs:
            if ref.url:
                yield config.id, ref.law or "", ref.url


def test_legal_refs_consistency():
    """Текст law: должен упоминать закон, на который ведёт consultant-ссылка.

    Ловит подмену документа (например, текст про ФЗ-289, а URL ведёт на ПП №2463),
    а также ссылки на LAW_XXX, которых нет в реестре legal_sources. Закрытые источники
    (normativ.kontur/cbr.ru/pravo.gov.ru) пропускаются — их проверяют вручную.
    """
    from app.situations.legal_sources import check_consistency

    problems = []
    for situation_id, law, url in _all_legal_refs():
        res = check_consistency(law, url)
        if res["status"] == "mismatch":
            problems.append(f"{situation_id}: «{law}» → URL ведёт на {res['expected']}")
        elif res["status"] == "unknown":
            problems.append(
                f"{situation_id}: «{law}» → неизвестный документ {res['doc_id']} "
                "(добавьте в legal_sources.py)"
            )

    assert not problems, "Рассинхрон law: и URL:\n" + "\n".join(problems)
