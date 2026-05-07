from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.situations.registry import registry
from app.situations.models import WizardStep

router = APIRouter()


class SituationOut(BaseModel):
    id: str
    category: str
    title: str
    blurb: str
    examples: str
    document_type: str


class SituationDetailOut(SituationOut):
    wizard_steps: list[WizardStep]
    template_ready: bool


@router.get("/", response_model=list[SituationOut])
def list_situations() -> list[SituationOut]:
    return [
        SituationOut(
            id=c.id,
            category=c.category,
            title=c.title,
            blurb=c.blurb,
            examples=c.examples,
            document_type=c.document_type,
        )
        for c in registry.all()
    ]


@router.get("/{situation_id}", response_model=SituationDetailOut)
def get_situation(situation_id: str) -> SituationDetailOut:
    config = registry.get(situation_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Situation not found")
    return SituationDetailOut(
        id=config.id,
        category=config.category,
        title=config.title,
        blurb=config.blurb,
        examples=config.examples,
        document_type=config.document_type,
        wizard_steps=config.wizard_steps,
        template_ready=config.template_file is not None,
    )
