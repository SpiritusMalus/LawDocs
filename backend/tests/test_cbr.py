"""Tests for fetch_cb_rate() — CBR SOAP API parsing."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

_SOAP_RESPONSE_OK = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:web="http://web.cbr.ru/">
  <soap:Body>
    <web:KeyRateResponse>
      <web:KeyRateResult>
        <web:KR>
          <web:KRW>
            <web:DT>2026-05-15T00:00:00</web:DT>
            <web:Rate>20</web:Rate>
          </web:KRW>
          <web:KRW>
            <web:DT>2026-05-25T00:00:00</web:DT>
            <web:Rate>21</web:Rate>
          </web:KRW>
        </web:KR>
      </web:KeyRateResult>
    </web:KeyRateResponse>
  </soap:Body>
</soap:Envelope>"""

_SOAP_RESPONSE_EMPTY = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:web="http://web.cbr.ru/">
  <soap:Body>
    <web:KeyRateResponse>
      <web:KeyRateResult>
        <web:KR/>
      </web:KeyRateResult>
    </web:KeyRateResponse>
  </soap:Body>
</soap:Envelope>"""


@pytest.mark.anyio
async def test_fetch_cb_rate_parses_xml():
    mock_resp = MagicMock()
    mock_resp.text = _SOAP_RESPONSE_OK
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.cbr.httpx.AsyncClient", return_value=mock_client):
        from app.services.cbr import fetch_cb_rate
        result = await fetch_cb_rate()

    assert result == Decimal("21")


@pytest.mark.anyio
async def test_fetch_cb_rate_returns_none_on_http_error():
    import httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    with patch("app.services.cbr.httpx.AsyncClient", return_value=mock_client):
        from app.services.cbr import fetch_cb_rate
        result = await fetch_cb_rate()

    assert result is None


@pytest.mark.anyio
async def test_fetch_cb_rate_returns_none_on_empty_response():
    mock_resp = MagicMock()
    mock_resp.text = _SOAP_RESPONSE_EMPTY
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.cbr.httpx.AsyncClient", return_value=mock_client):
        from app.services.cbr import fetch_cb_rate
        result = await fetch_cb_rate()

    assert result is None
