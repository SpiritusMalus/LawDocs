"""
LLM-сервис: GigaChat.

GigaChat API совместим с OpenAI-форматом (chat completions).
Авторизация: OAuth2 через RqUID + Base64(client_id:client_secret).
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_gigachat_token: str | None = None
_gigachat_token_expires_at: datetime | None = None
_gigachat_lock = asyncio.Lock()

GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"


async def _get_gigachat_token() -> str:
    global _gigachat_token, _gigachat_token_expires_at

    async with _gigachat_lock:
        if (
            _gigachat_token
            and _gigachat_token_expires_at
            and _gigachat_token_expires_at > datetime.now(UTC)
        ):
            return _gigachat_token

        # verify=False: GigaChat использует CA «МинЦифры России», не входящий
        # в стандартный доверенный список. В продакшне можно добавить CA-cert
        # через httpx.AsyncClient(verify="/path/to/mintsifry_ca.pem").
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                GIGACHAT_AUTH_URL,
                headers={
                    "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=10,
            )
            if not resp.is_success:
                logger.error("GigaChat auth failed %s: %s", resp.status_code, resp.text)
                resp.raise_for_status()
            data = resp.json()

        _gigachat_token = data["access_token"]
        _gigachat_token_expires_at = datetime.fromtimestamp(data["expires_at"] / 1000, tz=UTC)
        return _gigachat_token


async def _call_gigachat(system_prompt: str, user_prompt: str) -> str:
    token = await _get_gigachat_token()
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(
            f"{GIGACHAT_API_URL}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": "GigaChat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


_MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря"]

_DEFAULT_SYSTEM_PROMPT = """Ты — опытный юрист. Составь официальную претензию или жалобу.
Используй официально-деловой стиль. Ссылайся только на реальные нормы российского права.

Правила:
- Официально-деловой стиль, без эмоций и просторечий
- Ссылайся на конкретные статьи закона (не выдумывай несуществующие)
- Не придумывай факты — используй только данные пользователя
- Квадратные скобки [...] используй ТОЛЬКО для данных, которых нет в форме
- Все данные из формы вставляй напрямую — БЕЗ квадратных скобок
- Верни ТОЛЬКО текст документа, без пояснений и комментариев"""


def _build_user_prompt(situation_id: str, form_data: dict) -> str:
    now = datetime.now(UTC)
    today = f"{now.day} {_MONTHS_RU[now.month - 1]} {now.year} года"
    lines = [f"Ситуация: {situation_id}", f"Дата составления документа: {today}", "", "Данные пользователя:"]
    for k, v in form_data.items():
        if v:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


async def fill_template(situation_id: str, form_data: dict) -> str:
    from app.situations.registry import registry

    config = registry.get(situation_id)
    system_prompt = config.system_prompt if config else _DEFAULT_SYSTEM_PROMPT
    user_prompt = _build_user_prompt(situation_id, form_data)

    if not settings.GIGACHAT_AUTH_KEY:
        raise RuntimeError("GigaChat not configured — set GIGACHAT_AUTH_KEY")

    return await _call_gigachat(system_prompt, user_prompt)
