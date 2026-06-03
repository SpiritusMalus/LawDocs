"""
Situation registry: loads all YAML configs from the configs/ directory.
Each YAML file defines one situation: metadata, wizard steps, LLM prompts.
Adding a new situation = drop a new .yaml file, no code changes needed.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.situations.models import SituationConfig, WizardField, WizardStep

logger = logging.getLogger(__name__)

BASE_RULES = """Правила:
- Официально-деловой стиль, без эмоций и просторечий
- Ссылайся на конкретные статьи закона (не выдумывай несуществующие)
- Не придумывай факты — используй только данные пользователя
- Квадратные скобки [...] используй ТОЛЬКО для данных, которых нет в форме и которые пользователь впишет вручную
- Все данные из формы (ФИО, адрес, даты, суммы, названия) вставляй напрямую — БЕЗ квадратных скобок
- Даты из формы в формате ГГГГ-ММ-ДД переводи в русский формат: «1 мая 2026 года»
- Для строки подписи в конце используй: «_________________ / _________________»
- Верни ТОЛЬКО текст документа, без пояснений и комментариев"""

CONTACT_STEP = WizardStep(
    title="Ваши контакты",
    fields=[
        WizardField(id="full_name", type="text", label="ФИО", placeholder="Иванов Иван Иванович", required=True, max_len=150),
        # Адрес заполняется по частям — так в документ не уходит опечатка в составе
        # «одной строкой». Подполя детерминированно собираются в contact_address
        # (см. services/address_compose.py). Все части НЕобязательны по отдельности
        # (село без улицы, корпус без дома и т.п.), но хотя бы одна должна быть
        # заполнена — проверяется в validate_address. Индекс не нужен для шапки.
        WizardField(id="address_city", type="text", label="Город / населённый пункт", placeholder="Москва", hint="Город, посёлок, село, деревня", max_len=100),
        WizardField(id="address_street", type="text", label="Улица", placeholder="Пушкина (или пер./просп.)", max_len=150),
        WizardField(id="address_house", type="text", label="Дом / владение", placeholder="1", max_len=20),
        WizardField(id="address_building", type="text", label="Корпус", placeholder="2", max_len=20),
        WizardField(id="address_structure", type="text", label="Строение", placeholder="1", max_len=20),
        WizardField(id="address_apartment", type="text", label="Квартира", placeholder="5", max_len=20),
        WizardField(id="phone", type="text", label="Телефон", placeholder="+7 999 123-45-67", required=True, max_len=20),
        WizardField(id="email", type="text", label="Email", placeholder="ivan@mail.ru", required=True, hint="Готовый документ пришлём сюда", max_len=254),
    ],
)


def _load_yaml(path: Path) -> SituationConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    append_contact = data.pop("append_contact_step", True)

    raw_prompt = data.get("system_prompt", "")
    data["system_prompt"] = f"{raw_prompt.strip()}\n\n{BASE_RULES}"

    config = SituationConfig(**data, append_contact_step=append_contact)

    if append_contact:
        config = config.model_copy(update={"wizard_steps": config.wizard_steps + [CONTACT_STEP]})

    return config


class SituationRegistry:
    def __init__(self) -> None:
        self._configs: dict[str, SituationConfig] = {}

    def load(self, configs_dir: Path) -> None:
        self._configs.clear()
        for yaml_file in sorted(configs_dir.rglob("*.yaml")):
            try:
                config = _load_yaml(yaml_file)
                self._configs[config.id] = config
            except Exception as exc:
                raise ValueError(f"Invalid situation config {yaml_file.name}: {exc}") from exc
        logger.info("Loaded %d situation configs from %s", len(self._configs), configs_dir)

    def get(self, situation_id: str) -> SituationConfig | None:
        return self._configs.get(situation_id)

    def all(self) -> list[SituationConfig]:
        return list(self._configs.values())

    def ids(self) -> set[str]:
        return set(self._configs.keys())

    def all_field_ids(self) -> frozenset[str]:
        return frozenset(
            field.id
            for config in self._configs.values()
            for step in config.wizard_steps
            for field in step.fields
        )

    def __len__(self) -> int:
        return len(self._configs)


registry = SituationRegistry()
