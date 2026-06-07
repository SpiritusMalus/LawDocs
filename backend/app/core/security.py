import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"

# PBKDF2-HMAC-SHA256 для пароля аккаунта. Stdlib — без новых зависимостей.
# 600k итераций — рекомендация OWASP (2023) для PBKDF2-SHA256.
_PBKDF2_ITERATIONS = 600_000


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        exp = payload.get("exp")
        if not user_id or not exp:
            return None
        return user_id
    except JWTError:
        return None


def get_token_remaining_seconds(token: str) -> float:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if not exp:
            return 0
        return max(0.0, exp - datetime.now(UTC).timestamp())
    except JWTError:
        return 0


def generate_magic_token() -> str:
    return secrets.token_urlsafe(32)


def hash_magic_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_guest_token() -> str:
    """Секрет доступа гостя к одному заказу (cookie order_token)."""
    return secrets.token_urlsafe(32)


def hash_guest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_challenge_nonce(nonce: bytes) -> str:
    """Хэш nonce для challenge-response логина (сверка без хранения самого nonce)."""
    return hashlib.sha256(nonce).hexdigest()


def hash_password(password: str) -> str:
    """Хэш пароля аккаунта: pbkdf2_sha256$iterations$salt$hash (base64)."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${_PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"
    )


def verify_password(password: str, stored: str) -> bool:
    """Проверяет пароль против сохранённого хэша (constant-time)."""
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt_b64), int(iterations)
        )
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False
