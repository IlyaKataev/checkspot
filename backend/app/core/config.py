from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 дней

    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_URL: str | None = None

    MEDIA_DIR: str = "./media/photos"

    TWOGIS_API_KEY: str = ""

    AI_MODERATION_ENABLED: bool = False
    ANTHROPIC_API_KEY: str = ""

    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def async_database_url(self) -> str:
        """Railway отдаёт postgresql://, SQLAlchemy async требует postgresql+asyncpg://"""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
