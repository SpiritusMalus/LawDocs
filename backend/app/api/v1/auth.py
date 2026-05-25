import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import (
    ContactOut,
    E2EESetupRequest,
    E2EESetupResponse,
    RecoverAccessRequest,
    RecoverAccessResponse,
    VerifyOut,
)
from app.schemas.user import MagicLinkRequest, UserOut
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/contact", response_model=ContactOut)
async def get_my_contact(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    return await auth_service.get_user_contact(current_user, db)


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def request_magic_link(
    request: Request,
    body: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else "unknown"
    await auth_service.request_magic_link(body.email.lower(), ip, db)


@router.get("/verify", response_model=VerifyOut)
@limiter.limit("20/minute")
async def verify_magic_link(
    request: Request,
    token: str,
    order: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> VerifyOut:
    """
    Verifies a magic link token. Returns JWT in body so Next.js Route Handler
    can set the httpOnly cookie for the correct frontend domain.
    """
    user, access_token = await auth_service.verify_magic_link(token, db)
    return VerifyOut(
        access_token=access_token,
        order_id=order,
        user=UserOut.model_validate(user),
    )


# ============================================================================
# E2EE ENDPOINTS
# ============================================================================


@router.post("/setup-e2ee", response_model=E2EESetupResponse)
async def setup_e2ee(
    request: Request,
    body: E2EESetupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> E2EESetupResponse:
    """
    Zero-knowledge: сервер получает public_key и зашифрованный blob.
    Фраза восстановления НИКОГДА не уходит на сервер — браузер шифрует ею
    private_key и отправляет непрозрачный blob. Сервер хранит blob и не может
    его расшифровать без фразы.
    """
    ip = request.client.host if request.client else "unknown"
    return await auth_service.setup_e2ee(current_user, body, ip, db)


@router.post("/recover-access", response_model=RecoverAccessResponse)
@limiter.limit("5/minute")
async def recover_access(
    request: Request,
    body: RecoverAccessRequest,
    db: AsyncSession = Depends(get_db),
) -> RecoverAccessResponse:
    """
    Zero-knowledge recovery: сервер возвращает зашифрованный blob (Fernet снят),
    браузер расшифровывает его парольной фразой локально. Фраза на сервер не идёт.
    """
    ip = request.client.host if request.client else "unknown"
    return await auth_service.recover_access(body.email.lower(), ip, db)
