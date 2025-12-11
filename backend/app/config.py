from pydantic_settings import BaseSettings
from typing import Optional
import os

CURRENT_ENV = os.getenv("ENV", "development").lower()

class Settings(BaseSettings):
    # Database
    database_url: str

    # Seguridad
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # SMTP
    email_host: str
    email_port: int
    email_username: str
    email_password: str
    emails_from_name: str
    emails_from_email: str

    # URLs
    frontend_url: str
    api_url: str

    # Gemini API
    gemini_api_key: Optional[str] = None

    # Entorno y debug
    environment: str = CURRENT_ENV
    debug: bool = CURRENT_ENV != "production"
    docs_enabled: bool = CURRENT_ENV != "production"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  

def get_settings():
    if CURRENT_ENV == "production":
        return Settings(
            database_url=os.getenv("DATABASE_URL_PROD"),
            email_host=os.getenv("SMTP_HOST"),
            email_port=int(os.getenv("SMTP_PORT", 587)),
            email_username=os.getenv("SMTP_USER"),
            email_password=os.getenv("SMTP_PASSWORD"),
            emails_from_name=os.getenv("EMAILS_FROM_NAME"),
            emails_from_email=os.getenv("EMAILS_FROM_EMAIL"),
            frontend_url=os.getenv("FRONTEND_URL_PROD"),
            api_url=os.getenv("API_URL_PROD"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
        )
    else:
        return Settings(
            database_url=os.getenv("DATABASE_URL_DEV"),
            email_host=os.getenv("SMTP_HOST"),
            email_port=int(os.getenv("SMTP_PORT", 587)),
            email_username=os.getenv("SMTP_USER"),
            email_password=os.getenv("SMTP_PASSWORD"),
            emails_from_name=os.getenv("EMAILS_FROM_NAME"),
            emails_from_email=os.getenv("EMAILS_FROM_EMAIL"),
            frontend_url=os.getenv("FRONTEND_URL_DEV"),
            api_url=os.getenv("API_URL_DEV"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
        )

settings = get_settings()

def is_production() -> bool:
    return settings.environment == "production"

def get_cors_origins() -> list:
    if is_production():
        return [settings.frontend_url]
    else:
        return [
            "http://localhost:4200",
            "http://127.0.0.1:4200",
            settings.frontend_url
        ]
