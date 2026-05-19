from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str  # openssl rand -hex 32

    @field_validator("SECRET_KEY")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters (run: openssl rand -hex 32)")
        return v
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/lawdocs

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    MAGIC_LINK_EXPIRE_MINUTES: int = 15

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_TLS: bool = True
    SMTP_STARTTLS: bool = False
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@lawdocs.ru"

    # GigaChat — Authorization Key из консоли разработчика (уже готовый Base64)
    GIGACHAT_AUTH_KEY: str = ""
    # Путь к PEM-файлу с CA Минцифры России для верификации TLS GigaChat.
    # Скачать: https://www.gosuslugi.ru/crt  → «Корневой сертификат»
    # Если пусто — TLS-верификация отключена (не рекомендуется для production).
    GIGACHAT_CA_CERT: str = ""

    # ЮKassa
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""

    # File storage — Яндекс Object Storage (S3-совместимый)
    S3_ENDPOINT_URL: str = "https://storage.yandexcloud.net"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "ru-central1"

    # Frontend URL (for magic link redirects)
    FRONTEND_URL: str = "https://lawdocs.ru"

    # Шифрование ПДн в form_data (152-ФЗ)
    # Генерация: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    FERNET_KEY: str = ""

    # Telegram-алерты (опционально — если пусто, алерты отключены)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""


settings = Settings()  # type: ignore[call-arg]
