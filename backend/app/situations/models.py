from __future__ import annotations

from typing import Literal
from pydantic import BaseModel


class WizardFieldOption(BaseModel):
    value: str
    label: str


class WizardField(BaseModel):
    id: str
    type: Literal["text", "number", "date", "textarea", "radio"]
    label: str
    placeholder: str | None = None
    required: bool = False
    hint: str | None = None
    options: list[WizardFieldOption] | None = None


class WizardStep(BaseModel):
    title: str
    fields: list[WizardField]


class SituationConfig(BaseModel):
    id: str
    category: str
    title: str
    blurb: str
    examples: str = ""
    document_type: str = "pretenziya"
    template_file: str | None = None
    system_prompt: str
    ai_narrative_prompt: str | None = None
    wizard_steps: list[WizardStep]
    append_contact_step: bool = True
