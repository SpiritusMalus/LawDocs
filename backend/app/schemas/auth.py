from pydantic import BaseModel

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


class RecoverAccessResponse(BaseModel):
    backup_encrypted: str  # blob зашифрован фразой пользователя — сервер его не читает
    message: str
