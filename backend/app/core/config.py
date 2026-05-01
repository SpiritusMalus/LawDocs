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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    MAGIC_LINK_EXPIRE_MINUTES: int = 15

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@lawdocs.ru"

    # GigaChat
    GIGACHAT_CLIENT_ID: str = ""
    GIGACHAT_CLIENT_SECRET: str = ""

    # Claude (fallback)
    ANTHROPIC_API_KEY: str = ""

    # ЮKassa
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""

    # S3 / file storage
    S3_ENDPOINT: str = ""       # Selectel / Timeweb S3-совместимое хранилище
    S3_BUCKET: str = "lawdocs-documents"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # Frontend URL (for magic link redirects)
    FRONTEND_URL: str = "https://lawdocs.ru"


settings = Settings()  # type: ignore[call-arg]
