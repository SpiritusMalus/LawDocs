"""Tests for legal_refs HTTP link checking."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services import link_check


def _cfg(situation_id, refs):
    return SimpleNamespace(
        id=situation_id,
        legal_refs=[SimpleNamespace(law=law, url=url) for law, url in refs],
    )


def _resp(status, url):
    return SimpleNamespace(status_code=status, url=url)


def _client_returning(mapping):
    """Fake AsyncClient whose head() returns response per-URL from mapping."""
    client = AsyncMock()

    async def head(url, headers=None):
        val = mapping[url]
        if isinstance(val, Exception):
            raise val
        return _resp(val, url)

    client.head.side_effect = head
    client.get.side_effect = head
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


@pytest.mark.asyncio
async def test_classifies_ok_and_broken():
    configs = [
        _cfg("shop", [("ЗоЗПП ст. 18", "https://x.test/ok")]),
        _cfg("bank", [("ГК ст. 845", "https://x.test/missing")]),
    ]
    mapping = {"https://x.test/ok": 200, "https://x.test/missing": 404}
    with (
        patch.object(link_check.registry, "all", return_value=configs),
        patch.object(link_check.httpx, "AsyncClient", return_value=_client_returning(mapping)),
    ):
        results = await link_check.check_legal_refs()

    by_url = {r["url"]: r for r in results}
    assert by_url["https://x.test/ok"]["ok"] is True
    assert by_url["https://x.test/missing"]["ok"] is False
    assert by_url["https://x.test/missing"]["status"] == 404


@pytest.mark.asyncio
async def test_dedupes_url_but_lists_all_situations():
    url = "https://x.test/shared"
    configs = [
        _cfg("shop", [("ЗоЗПП ст. 18", url)]),
        _cfg("bank", [("ЗоЗПП ст. 16", url)]),
    ]
    client = _client_returning({url: 200})
    with (
        patch.object(link_check.registry, "all", return_value=configs),
        patch.object(link_check.httpx, "AsyncClient", return_value=client),
    ):
        results = await link_check.check_legal_refs()

    assert len(results) == 1
    assert client.head.await_count == 1
    assert results[0]["situations"] == ["bank", "shop"]
    assert results[0]["laws"] == ["ЗоЗПП ст. 16", "ЗоЗПП ст. 18"]


@pytest.mark.asyncio
async def test_network_error_marks_not_ok():
    url = "https://x.test/timeout"
    configs = [_cfg("shop", [("ЗоЗПП ст. 18", url)])]
    mapping = {url: httpx.ConnectTimeout("timed out")}
    with (
        patch.object(link_check.registry, "all", return_value=configs),
        patch.object(link_check.httpx, "AsyncClient", return_value=_client_returning(mapping)),
    ):
        results = await link_check.check_legal_refs()

    assert results[0]["ok"] is False
    assert results[0]["status"] is None
    assert "ConnectTimeout" in results[0]["error"]


@pytest.mark.asyncio
async def test_empty_refs_returns_empty():
    configs = [_cfg("shop", []), _cfg("bank", [("закон без url", "")])]
    with patch.object(link_check.registry, "all", return_value=configs):
        results = await link_check.check_legal_refs()
    assert results == []
