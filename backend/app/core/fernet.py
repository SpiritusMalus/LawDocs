import json

from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

_fernet: MultiFernet | None = None


def _get_fernet() -> MultiFernet:
    global _fernet
    if _fernet is None:
        from app.core.config import settings
        keys = settings.fernet_keys_list
        if not keys:
            raise RuntimeError(
                "FERNET_KEY (или FERNET_KEYS) не задан. Сгенерируйте ключ:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "и добавьте FERNET_KEY=<ключ> в .env"
            )
        _fernet = MultiFernet([Fernet(k.encode()) for k in keys])
    return _fernet


class EncryptedJSON(TypeDecorator):
    """JSON-колонка, прозрачно шифруемая Fernet (AES-128-CBC + HMAC-SHA256)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _get_fernet().encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(_get_fernet().decrypt(value.encode()).decode())
