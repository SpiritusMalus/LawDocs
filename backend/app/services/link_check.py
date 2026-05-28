"""
Проверка доступности ссылок на законодательство (legal_refs) из конфигов ситуаций.

Чисто HTTP-проверка (httpx), без LLM: бьём по каждому уникальному URL и смотрим,
жив ли он. Содержательную актуальность законов отслеживает law_monitor отдельно.
"""

import asyncio
import logging

import httpx

from app.situations.registry import registry

logger = logging.getLogger(__name__)

_USER_AGENT = "LawDocs-LinkCheck/1.0 (lawdocsru@gmail.com)"
_CONCURRENCY = 5
_TIMEOUT = 20.0


async def _check_url(client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore) -> dict:
    result: dict = {"url": url, "status": None, "ok": False, "redirected_to": None, "error": None}
    async with sem:
        try:
            resp = await client.head(url, headers={"User-Agent": _USER_AGENT})
            if resp.status_code in (403, 405, 501):
                resp = await client.get(url, headers={"User-Agent": _USER_AGENT})
            result["status"] = resp.status_code
            result["ok"] = 200 <= resp.status_code < 400
            if str(resp.url) != url:
                result["redirected_to"] = str(resp.url)
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
    return result


async def check_legal_refs() -> list[dict]:
    """Проверяет все уникальные legal_refs.url. Возвращает по одному dict на URL.

    Каждый элемент: {url, status, ok, redirected_to, error, situations, laws}.
    Один URL может встречаться в нескольких ситуациях — проверяем его один раз,
    но в отчёте перечисляем все ситуации и формулировки закона.
    """
    by_url: dict[str, dict[str, set[str]]] = {}
    for cfg in registry.all():
        for ref in cfg.legal_refs:
            if not ref.url:
                continue
            entry = by_url.setdefault(ref.url, {"situations": set(), "laws": set()})
            entry["situations"].add(cfg.id)
            if ref.law:
                entry["laws"].add(ref.law)

    if not by_url:
        return []

    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        checks = await asyncio.gather(*(_check_url(client, url, sem) for url in by_url))

    results: list[dict] = []
    for check in checks:
        meta = by_url[check["url"]]
        check["situations"] = sorted(meta["situations"])
        check["laws"] = sorted(meta["laws"])
        results.append(check)

    broken = sum(1 for r in results if not r["ok"])
    logger.info("link_check_done", extra={"action": "link_check_done", "total": len(results), "broken": broken})
    return results
