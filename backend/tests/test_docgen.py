"""Tests for document generation (docx/pdf pipeline)."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.docgen import (
    _sanitize_situation_id,
    _sanitize_order_id,
    _text_to_docx,
    _find_template,
)


def test_sanitize_situation_id_valid():
    assert _sanitize_situation_id("shop") == "shop"
    assert _sanitize_situation_id("shop_defect") == "shop_defect"
    assert _sanitize_situation_id("a" * 32) == "a" * 32


def test_sanitize_situation_id_invalid():
    with pytest.raises(ValueError):
        _sanitize_situation_id("../etc/passwd")
    with pytest.raises(ValueError):
        _sanitize_situation_id("SHOP")
    with pytest.raises(ValueError):
        _sanitize_situation_id("shop-defect")
    with pytest.raises(ValueError):
        _sanitize_situation_id("")
    with pytest.raises(ValueError):
        _sanitize_situation_id("a" * 65)


def test_sanitize_order_id_valid():
    valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
    assert _sanitize_order_id(valid_uuid) == valid_uuid


def test_sanitize_order_id_invalid():
    with pytest.raises(ValueError):
        _sanitize_order_id("../etc/passwd")
    with pytest.raises(ValueError):
        _sanitize_order_id("not-a-uuid")
    with pytest.raises(ValueError):
        _sanitize_order_id("")


def test_text_to_docx_returns_bytes():
    content = "Первая строка\nВторая строка\nТретья строка"
    result = _text_to_docx(content)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # DOCX files start with PK (zip header)
    assert result[:2] == b"PK"


def test_text_to_docx_empty():
    result = _text_to_docx("")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_find_template_returns_none_when_no_templates(tmp_path):
    with patch("app.services.docgen.TEMPLATES_DIR", tmp_path):
        result = _find_template("shop", {"problem_type": "defect"})
        assert result is None


def test_find_template_finds_subtype(tmp_path):
    subtype_dir = tmp_path / "shop"
    subtype_dir.mkdir()
    template = subtype_dir / "defect.docx"
    template.write_bytes(b"fake docx")

    with patch("app.services.docgen.TEMPLATES_DIR", tmp_path):
        result = _find_template("shop", {"problem_type": "defect"})
        assert result == template


def test_find_template_falls_back_to_situation(tmp_path):
    template = tmp_path / "shop.docx"
    template.write_bytes(b"fake docx")

    with patch("app.services.docgen.TEMPLATES_DIR", tmp_path):
        # No subtype match, falls back to shop.docx
        result = _find_template("shop", {"problem_type": "nonexistent"})
        assert result == template


@pytest.mark.asyncio
async def test_generate_document_text_fallback(tmp_path):
    """When no template exists, falls back to text-to-docx."""
    with (
        patch("app.services.docgen.TEMPLATES_DIR", tmp_path),
        patch("app.services.docgen.settings") as mock_settings,
        patch("app.services.docgen._docx_to_pdf", return_value=b"%PDF fake"),
    ):
        mock_settings.DOCUMENTS_DIR = str(tmp_path)
        from app.services.docgen import generate_document
        docx_name, pdf_name = await generate_document(
            order_id="550e8400-e29b-41d4-a716-446655440000",
            situation_id="shop",
            content="Текст претензии",
            form_data={"problem_type": "defect"},
        )
        assert docx_name.startswith("pretenziya_shop_")
        assert docx_name.endswith(".docx")
        assert pdf_name.endswith(".pdf")
