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

    from app.situations.legal_sources import is_manual_source

    results.sort(key=lambda r: (r["ok"], r["url"]))
    broken = 0
    manual_down = 0
    for r in results:
        mark = "✓" if r["ok"] else "✗"
        status = r["status"] if r["status"] is not None else r.get("error", "—")
        situations = ", ".join(r["situations"])
        print(f"{mark} [{status}] {r['url']}")
        print(f"    ситуации: {situations}")
        if r["redirected_to"]:
            print(f"    → редирект: {r['redirected_to']}")
        if not r["ok"]:
            # Закрытые источники (normativ/cbr/pravo) недоступны для бота и часто
            # отдают ошибку — это не повод падать, их проверяют вручную.
            if is_manual_source(r["url"]):
                manual_down += 1
            else:
                broken += 1

    # Рассинхроны: текст law: не соответствует закону, на который ведёт URL.
    mismatched = [r for r in results if r.get("mismatches")]
    if mismatched:
        print("\n⚠ РАССИНХРОН текста и ссылки (закон в law: ≠ документ в URL):")
        for r in mismatched:
            for m in r["mismatches"]:
                expected = m["expected"] or f"неизвестный документ {m['doc_id']}"
                print(f"  ✗ «{m['law']}»")
                print(f"      URL ведёт на: {expected} ({r['url']})")

    total = len(results)
    miss = sum(len(r["mismatches"]) for r in mismatched)
    print(
        f"\nИтого: проблемных consultant-ссылок: {broken}, рассинхронов: {miss}, "
        f"закрытых источников недоступно (проверить вручную): {manual_down} из {total}"
    )
    return 1 if (broken or miss) else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
