from pydantic import BaseModel, Field, field_validator

from app.core.validators import Email, reject_blocked_email
from app.schemas.user import UserOut


class VerifyOut(BaseModel):
    access_token: str
    order_id: str | None = None
    user: UserOut


class ContactOut(BaseModel):
    full_name: str = ""
    phone: str = ""
    contact_address: str = ""  # legacy: собранный адрес из старых заказов
    address_city: str = ""
    address_street: str = ""
    address_house: str = ""
    address_building: str = ""
    address_structure: str = ""
    address_apartment: str = ""
    email: str = ""


class E2EESetupRequest(BaseModel):
    public_key: str
    encrypted_backup: str  # AES-GCM(private_key, PBKDF2(phrase)) — браузер шифрует сам


class E2EESetupResponse(BaseModel):
    status: str
    message: str


class RecoverAccessRequest(BaseModel):
    email: str
    # recovery_password намеренно УБРАН: фраза не должна уходить на сервер.
    # Браузер получит зашифрованный blob и расшифрует его локально.

    @field_validator("email")
    @classmethod
    def block_gmail(cls, v: str) -> str:
        return reject_blocked_email(v)


class RecoverAccessResponse(BaseModel):
    backup_encrypted: str  # blob зашифрован фразой пользователя — сервер его не читает
    message: str


# ============================================================================
# LOGIN BY KEY (challenge-response на keypair)
# ============================================================================


class KeyChallengeRequest(BaseModel):
    public_key: str  # base64 публичного ключа из key-файла пользователя


class KeyChallengeResponse(BaseModel):
    challenge_id: str
    # nonce, зашифрованный на public_key (формат как у decryptFormData).
    # Расшифровать может только владелец приватного ключа.
    encrypted_challenge: str


class KeyLoginRequest(BaseModel):
    challenge_id: str
    nonce: str  # base64 расшифрованного nonce — доказательство владения ключом


class KeyLoginResponse(BaseModel):
    access_token: str
    user: UserOut


# ============================================================================
# KEYRING под паролем аккаунта (вторая дверь к тем же ключам)
# ============================================================================


class WrappedKeyIn(BaseModel):
    public_key: str
    # blob, зашифрованный паролем НА КЛИЕНТЕ — сервер хранит непрозрачно.
    wrapped_private_key: str
    label: str | None = None


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    # Ключи, обёрнутые этим же паролем в браузере (обычно текущий ключ устройства).
    wrapped_keys: list[WrappedKeyIn] = Field(default_factory=list)


class SetPasswordResponse(BaseModel):
    status: str
    keys_stored: int


class PasswordLoginRequest(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=128)


class KeyringEntryOut(BaseModel):
    public_key: str
    wrapped_private_key: str
    label: str | None = None


class PasswordLoginResponse(BaseModel):
    access_token: str
    user: UserOut
    # Весь keyring — браузер раскроет каждый ключ паролем и расшифрует заказы.
    keyring: list[KeyringEntryOut]


# ============================================================================
# KEY MERGING — импорт нескольких ключ-файлов в keyring под одним паролем
# ============================================================================


class KeyringImportRequest(BaseModel):
    # Пароль аккаунта — сверяем его на сервере, чтобы все blob'ы в keyring были
    # обёрнуты одним и тем же (верным) паролем. Сам пароль не сохраняем.
    password: str = Field(min_length=8, max_length=128)
    wrapped_keys: list[WrappedKeyIn] = Field(min_length=1)


class KeyringImportResponse(BaseModel):
    status: str
    total_keys: int  # сколько ключей в keyring после импорта


class KeyringItemOut(BaseModel):
    """Метаданные ключа для UI — без самого обёрнутого ключа."""

    public_key: str
    label: str | None = None


class KeyringListResponse(BaseModel):
    keys: list[KeyringItemOut]
