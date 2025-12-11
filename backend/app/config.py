from pydantic_settings import BaseSettings
from typing import Optional
import os


CURRENT_ENV = os.getenv("ENV", os.getenv("RAILWAY_ENVIRONMENT", "development")).lower()


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:chAVuwbfFRQeTppuvhpbMhkVGfkBqvqZ@maglev.proxy.rlwy.net:29893/railway")
    secret_key: str = os.getenv("SECRET_KEY", "INSECURE_DEV_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    email_host: str = "smtp.gmail.com"
    email_port: int = 587
    email_username: str = os.getenv("EMAIL_USERNAME", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    emails_from_name: str = os.getenv("EMAILS_FROM_NAME", "Kaimo")
    emails_from_email: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@kaimo.com")

    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")

    frontend_url: str = os.getenv("FRONTEND_URL", "kaimox.up.railway.app")
    api_url: str = os.getenv("API_URL", "backkaimo.up.railway.app")

    environment: str = CURRENT_ENV
    debug: bool = CURRENT_ENV != "production"
    docs_enabled: bool = CURRENT_ENV != "production"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()


def is_production() -> bool:
    return settings.environment == "production"


def get_cors_origins() -> list:
    if is_production():
        return [
            settings.frontend_url,
            "kaimox.up.railway.app"
        ]

    return [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        settings.frontend_url,
        "kaimox.up.railway.app"
    ]
