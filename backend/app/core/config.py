from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str  # openssl rand -hex 32
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
    GIGACHAT_CLIENT_ID: str = ""  # не используется, оставлен для совместимости

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


settings = Settings()  # type: ignore[call-arg]
