"""
LLM-сервис: GigaChat основной, Claude — fallback.

GigaChat API совместим с OpenAI-форматом (chat completions).
Авторизация: OAuth2 через RqUID + Base64(client_id:client_secret).
"""

import base64
import logging
from datetime import UTC, datetime

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_gigachat_token: str | None = None
_gigachat_token_expires_at: datetime | None = None

GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"


async def _get_gigachat_token() -> str:
    global _gigachat_token, _gigachat_token_expires_at

    if _gigachat_token and _gigachat_token_expires_at and _gigachat_token_expires_at > datetime.now(UTC):
        return _gigachat_token

    credentials = base64.b64encode(
        f"{settings.GIGACHAT_CLIENT_ID}:{settings.GIGACHAT_CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient(verify=False) as client:  # GigaChat использует корпоративный CA
        resp = await client.post(
            GIGACHAT_AUTH_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "RqUID": "lawdocs-backend",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"scope": "GIGACHAT_API_PERS"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    _gigachat_token = data["access_token"]
    # expires_at приходит в миллисекундах
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
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_claude(system_prompt: str, user_prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


SYSTEM_PROMPT = """Ты — юридический ассистент. Твоя задача — заполнить шаблон документа
(претензию или жалобу) на основании данных, предоставленных пользователем.
Правила:
- Используй официально-деловой стиль
- Ссылайся на статьи закона там, где это предусмотрено шаблоном
- Не придумывай факты — используй только то, что сообщил пользователь
- Если какие-то данные отсутствуют, оставь плейсхолдер вида [УКАЖИТЕ ...]
- Верни ТОЛЬКО заполненный текст документа, без пояснений"""


async def fill_template(situation_id: str, form_data: dict) -> str:
    user_prompt = (
        f"Ситуация: {situation_id}\n\n"
        f"Данные пользователя:\n"
        + "\n".join(f"- {k}: {v}" for k, v in form_data.items())
    )

    if settings.GIGACHAT_CLIENT_ID:
        try:
            return await _call_gigachat(SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            logger.warning("GigaChat failed, falling back to Claude: %s", exc)

    if settings.ANTHROPIC_API_KEY:
        return await _call_claude(SYSTEM_PROMPT, user_prompt)

    raise RuntimeError("No LLM configured — set GIGACHAT_CLIENT_ID or ANTHROPIC_API_KEY")
