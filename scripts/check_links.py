"""
Ручная проверка доступности ссылок на законодательство (legal_refs).

Запуск: cd backend && .venv/bin/python ../scripts/check_links.py
Exit code 1, если есть недоступные ссылки.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.situations.registry import registry
from app.services.link_check import check_legal_refs


async def main() -> int:
    configs_dir = Path(__file__).parent.parent / "backend" / "app" / "situations" / "configs"
    registry.load(configs_dir)

    results = await check_legal_refs()
    if not results:
        print("Нет ссылок для проверки.")
        return 0

    results.sort(key=lambda r: (r["ok"], r["url"]))
    broken = 0
    for r in results:
        mark = "✓" if r["ok"] else "✗"
        status = r["status"] if r["status"] is not None else r.get("error", "—")
        situations = ", ".join(r["situations"])
        print(f"{mark} [{status}] {r['url']}")
        print(f"    ситуации: {situations}")
        if r["redirected_to"]:
            print(f"    → редирект: {r['redirected_to']}")
        if not r["ok"]:
            broken += 1

    total = len(results)
    print(f"\nИтого: {total - broken}/{total} доступны, проблемных: {broken}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
