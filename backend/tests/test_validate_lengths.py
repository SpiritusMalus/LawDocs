"""Tests for validate_lengths — explicit max_len vs default text cap."""

import pytest

from app.situations.models import SituationConfig, WizardField, WizardStep
from app.situations.validate import _DEFAULT_TEXT_MAX_LEN, validate_lengths


def _config(*fields: WizardField) -> SituationConfig:
    return SituationConfig(
        id="t",
        category="test",
        title="t",
        blurb="t",
        system_prompt="t",
        wizard_steps=[WizardStep(title="s", fields=list(fields))],
    )


def test_text_field_without_max_len_uses_default_cap():
    config = _config(WizardField(id="store_name", type="text", label="Магазин"))
    # На границе — ок.
    validate_lengths(config, {"store_name": "Я" * _DEFAULT_TEXT_MAX_LEN})
    # За границей — ValueError.
    with pytest.raises(ValueError, match="не более"):
        validate_lengths(config, {"store_name": "Я" * (_DEFAULT_TEXT_MAX_LEN + 1)})


def test_explicit_max_len_overrides_default():
    config = _config(WizardField(id="house", type="text", label="Дом", max_len=20))
    with pytest.raises(ValueError, match="не более 20"):
        validate_lengths(config, {"house": "1" * 21})


def test_textarea_without_max_len_is_not_capped_by_default():
    # Нарративам нужна длина — дефолтный text-кап на них не распространяется.
    config = _config(WizardField(id="problem", type="textarea", label="Проблема"))
    validate_lengths(config, {"problem": "Я" * (_DEFAULT_TEXT_MAX_LEN * 4)})
