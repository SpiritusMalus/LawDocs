#!/usr/bin/env python3
"""
Генерирует один документ и логирует raw GigaChat output перед постобработкой.
Запуск: cd backend && source .venv/bin/activate && python3 ../scripts/test_gigachat_raw.py
"""
import asyncio
import os
import sys
import uuid
import yaml
import httpx
from pathlib import Path

ROOT       = Path(__file__).parent.parent
ENV_FILE   = ROOT / "backend" / ".env"
DATA_FILE  = Path(__file__).parent / "sample_fake_data.yaml"
CONFIGS    = ROOT / "backend" / "app" / "situations" / "configs"
GIGA_AUTH  = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGA_API   = "https://gigachat.devices.sberbank.ru/api/v1"

sys.path.insert(0, str(ROOT / "backend"))
from app.services.text_cleanup import clean_llm_text, fix_dashes

# ── Load config ──

def load_env(path: Path) -> dict:
    env = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


def find_situation_config(situation_id: str) -> dict:
    for f in CONFIGS.rglob("*.yaml"):
        import yaml
        d = yaml.safe_load(f.read_text())
        if d.get("id") == situation_id:
            return d
    return {}


# ── GigaChat ──

async def get_token(auth_key: str) -> str:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            GIGA_AUTH,
            headers={"Authorization": f"Basic {auth_key}",
                     "RqUID": str(uuid.uuid4()),
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"scope": "GIGACHAT_API_PERS"}, timeout=15,
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def call_giga(token: str, system_prompt: str, user_prompt: str) -> str:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            f"{GIGA_API}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={"model": "GigaChat",
                  "messages": [{"role": "system", "content": system_prompt},
                                {"role": "user",   "content": user_prompt}],
                  "temperature": 0.2, "max_tokens": 4096},
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


# ── Main ──

async def main() -> None:
    env = load_env(ENV_FILE)
    auth_key = env.get("GIGACHAT_AUTH_KEY", "")
    if not auth_key:
        print("❌  GIGACHAT_AUTH_KEY не найден в backend/.env")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        situations = yaml.safe_load(f)

    # Test first situation (gym_refund usually)
    sit = situations[0]
    sid = sit["_id"]
    print(f"Testing: {sid}\n")

    config = find_situation_config(sid)
    if not config:
        print(f"❌ Конфиг не найден для {sid}")
        return

    system_prompt = config.get("system_prompt", "")
    if not system_prompt:
        print(f"❌ system_prompt не найден для {sid}")
        return

    # Build user prompt
    form_data = {k: v for k, v in sit.items() if not k.startswith("_")}
    user_prompt_lines = [f"Ситуация: {sid}", "", "Данные:"]
    for k, v in form_data.items():
        if v is not None and str(v).strip():
            user_prompt_lines.append(f"- {k}: {str(v)[:800]}")
    user_prompt = "\n".join(user_prompt_lines)

    print(f"System prompt length: {len(system_prompt)} chars\n")
    print("=" * 80)
    print("SYSTEM PROMPT:")
    print(system_prompt[:500] + "...\n")

    print("Getting GigaChat token…")
    token = await get_token(auth_key)

    print("Calling GigaChat…")
    raw_output = await call_giga(token, system_prompt, user_prompt)

    print("\n" + "=" * 80)
    print("RAW OUTPUT FROM GIGACHAT:")
    print("=" * 80)
    print(repr(raw_output))
    print("\n" + "=" * 80)
    print("RAW OUTPUT (PRETTY):")
    print("=" * 80)
    print(raw_output)

    print("\n" + "=" * 80)
    print("AFTER clean_llm_text():")
    print("=" * 80)
    cleaned = clean_llm_text(raw_output)
    print(cleaned)

    print("\n" + "=" * 80)
    print("AFTER fix_dashes():")
    print("=" * 80)
    final = fix_dashes(cleaned)
    print(final)

    # Check for all-caps issues
    print("\n" + "=" * 80)
    print("ANALYSIS:")
    print("=" * 80)
    for i, line in enumerate(final.split("\n"), 1):
        s = line.strip()
        if s and s.isupper() and len(s) > 10 and s not in {"ПРЕТЕНЗИЯ", "ЖАЛОБА", "ВОЗРАЖЕНИЕ", "ЗАЯВЛЕНИЕ", "ХОДАТАЙСТВО", "УВЕДОМЛЕНИЕ"}:
            print(f"Line {i}: ALL CAPS (unexpected): {s}")


if __name__ == "__main__":
    asyncio.run(main())
