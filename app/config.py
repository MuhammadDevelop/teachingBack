from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/online_teach"
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""  # e.g. https://your-app.onrender.com/webhook/telegram

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # Admin
    admin_phone: str = "998889810206"

    # Payment card info (shown to students)
    card_number: str = "5614 6819 0511 2722"
    card_holder: str = "Orifjonov Muhammaddiyor"
    card_expiry: str = "07/30"

    # Render
    render_external_url: str = ""
    port: int = 8000

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
