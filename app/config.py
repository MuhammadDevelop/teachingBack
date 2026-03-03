from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/online_teach"
    secret_key: str = "your-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    telegram_bot_token: str = ""
    frontend_url: str = "http://localhost:3000"
    payme_merchant_id: str = ""
    click_merchant_id: str = ""
    click_service_id: str = ""
    click_secret_key: str = ""

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
