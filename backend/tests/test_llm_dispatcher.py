"""Tests for _call_llm dispatcher — GigaChat primary, YandexGPT fallback."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.anyio
async def test_uses_gigachat_when_configured():
    with (
        patch("app.services.llm.settings") as mock_settings,
        patch("app.services.llm._call_gigachat", new_callable=AsyncMock) as mock_gc,
        patch("app.services.llm._call_yandex_primary", new_callable=AsyncMock) as mock_ya,
    ):
        mock_settings.GIGACHAT_AUTH_KEY = "somekey"
        mock_gc.return_value = "Текст документа"

        from app.services.llm import _call_llm
        result = await _call_llm("sys", "usr")

        assert result == "Текст документа"
        mock_gc.assert_called_once_with("sys", "usr", validate=False)
        mock_ya.assert_not_called()


@pytest.mark.anyio
async def test_falls_back_to_yandex_on_refusal():
    with (
        patch("app.services.llm.settings") as mock_settings,
        patch("app.services.llm._call_gigachat", new_callable=AsyncMock) as mock_gc,
        patch("app.services.llm._call_yandex_primary", new_callable=AsyncMock) as mock_ya,
    ):
        mock_settings.GIGACHAT_AUTH_KEY = "somekey"
        mock_settings.YANDEX_API_KEY = "yakey"
        mock_settings.YANDEX_FOLDER_ID = "folder123"
        mock_gc.return_value = "К сожалению, я не могу помочь с составлением данного документа."
        mock_ya.return_value = "Текст от Яндекса"

        from app.services.llm import _call_llm
        result = await _call_llm("sys", "usr")

        assert result == "Текст от Яндекса"
        mock_gc.assert_called_once()
        mock_ya.assert_called_once_with("sys", "usr")


@pytest.mark.anyio
async def test_falls_back_to_yandex_on_gigachat_exception():
    """Сбой GigaChat (сеть/TLS/сертификат) — исключение, не отказ. Должен
    фоллбэчить на Yandex, а не валить генерацию."""
    with (
        patch("app.services.llm.settings") as mock_settings,
        patch("app.services.llm._call_gigachat", new_callable=AsyncMock) as mock_gc,
        patch("app.services.llm._call_yandex_primary", new_callable=AsyncMock) as mock_ya,
    ):
        mock_settings.GIGACHAT_AUTH_KEY = "somekey"
        mock_settings.YANDEX_API_KEY = "yakey"
        mock_settings.YANDEX_FOLDER_ID = "folder123"
        mock_gc.side_effect = FileNotFoundError("CA cert missing")
        mock_ya.return_value = "Текст от Яндекса"

        from app.services.llm import _call_llm
        result = await _call_llm("sys", "usr")

        assert result == "Текст от Яндекса"
        mock_gc.assert_called_once()
        mock_ya.assert_called_once_with("sys", "usr")


@pytest.mark.anyio
async def test_reraises_gigachat_exception_when_yandex_unavailable():
    """Сбой GigaChat без настроенного Yandex — исключение пробрасывается."""
    with (
        patch("app.services.llm.settings") as mock_settings,
        patch("app.services.llm._call_gigachat", new_callable=AsyncMock) as mock_gc,
    ):
        mock_settings.GIGACHAT_AUTH_KEY = "somekey"
        mock_settings.YANDEX_API_KEY = ""
        mock_settings.YANDEX_FOLDER_ID = ""
        mock_gc.side_effect = FileNotFoundError("CA cert missing")

        from app.services.llm import _call_llm
        with pytest.raises(FileNotFoundError):
            await _call_llm("sys", "usr")


@pytest.mark.anyio
async def test_raises_when_both_unavailable():
    with (
        patch("app.services.llm.settings") as mock_settings,
    ):
        mock_settings.GIGACHAT_AUTH_KEY = ""
        mock_settings.YANDEX_API_KEY = ""
        mock_settings.YANDEX_FOLDER_ID = ""

        from app.services.llm import _call_llm
        with pytest.raises(RuntimeError, match="YandexGPT not configured"):
            await _call_llm("sys", "usr")


@pytest.mark.anyio
async def test_uses_yandex_when_gigachat_not_configured():
    with (
        patch("app.services.llm.settings") as mock_settings,
        patch("app.services.llm._call_gigachat", new_callable=AsyncMock) as mock_gc,
        patch("app.services.llm._call_yandex_primary", new_callable=AsyncMock) as mock_ya,
    ):
        mock_settings.GIGACHAT_AUTH_KEY = ""
        mock_settings.YANDEX_API_KEY = "yakey"
        mock_settings.YANDEX_FOLDER_ID = "folder123"
        mock_ya.return_value = "Текст от Яндекса"

        from app.services.llm import _call_llm
        result = await _call_llm("sys", "usr")

        assert result == "Текст от Яндекса"
        mock_gc.assert_not_called()
        mock_ya.assert_called_once_with("sys", "usr")
