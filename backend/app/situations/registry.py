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
        WizardField(id="full_name", type="text", label="ФИО", placeholder="Иванов Иван Иванович", required=True),
        WizardField(id="contact_address", type="text", label="Адрес проживания", placeholder="г. Москва, ул. Пушкина, д. 1, кв. 5", required=True, hint="Нужен для шапки претензии"),
        WizardField(id="phone", type="text", label="Телефон", placeholder="+7 999 123-45-67", required=True),
        WizardField(id="email", type="text", label="Email", placeholder="ivan@mail.ru", required=True, hint="Готовый документ пришлём сюда"),
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
            except Exception:
                logger.exception("Failed to load situation config: %s", yaml_file)
        logger.info("Loaded %d situation configs from %s", len(self._configs), configs_dir)

    def get(self, situation_id: str) -> SituationConfig | None:
        return self._configs.get(situation_id)

    def all(self) -> list[SituationConfig]:
        return list(self._configs.values())

    def ids(self) -> set[str]:
        return set(self._configs.keys())

    def __len__(self) -> int:
        return len(self._configs)


registry = SituationRegistry()
