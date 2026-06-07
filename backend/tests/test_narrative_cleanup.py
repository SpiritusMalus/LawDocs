"""Тесты на чистку нарратива от LLM-артефактов (мета-выжимки «В форме указано»)."""
from app.services.text_cleanup import clean_llm_text


def test_clean_strips_form_recap_header():
    """Заголовок-выжимка «В форме указано:» (мета-метка раздела) убирается."""
    text = "В форме указано:\n\n01.01.2024 произошло неправомерное списание средств."
    out = clean_llm_text(text)
    assert "В форме указано" not in out
    assert "неправомерное списание" in out


def test_clean_keeps_real_narrative():
    """Связный текст нарратива не выкидывается."""
    text = "Банк без согласия клиента списал денежные средства, что нарушает закон."
    out = clean_llm_text(text)
    assert "списал денежные средства" in out


def test_hybrid_narrative_runs_through_cleaner():
    """_fill_template_hybrid пропускает нарратив через clean_llm_text:
    мета-заголовок не доходит до итогового документа."""
    import asyncio
    from unittest.mock import patch

    from app.services import llm

    class _Config:
        narrative_fields = ["problem_desc"]
        narrative_prompt = "prompt"
        python_template = "{{llm_narrative}}\n\n[calculated_demand_section]"

    async def _fake_call(system, user, *, validate=False):
        return "В форме указано:\nФИО: Иванов Иван Иванович\n\nБанк незаконно списал средства."

    async def _run():
        with (
            patch.object(llm, "_call_llm", side_effect=_fake_call),
            patch.object(llm, "_get_yandex_provider") as gy,
        ):
            gy.return_value.review = _no_review
            return await llm._fill_template_hybrid(_Config(), {"problem_desc": "списали деньги"})

    async def _no_review(text):
        return text, False

    out = asyncio.run(_run())
    assert "В форме указано" not in out
    assert "незаконно списал" in out
