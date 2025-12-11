from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import os

CURRENT_ENV = os.getenv("ENV", "development").lower()

class Settings(BaseSettings):
    # Database
    database_url: Optional[str] = None
    database_url_prod: Optional[str] = None
    database_url_dev: Optional[str] = None

    # Seguridad
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # SMTP
    email_host: str = Field(alias="SMTP_HOST")
    email_port: int = Field(alias="SMTP_PORT")
    email_username: str = Field(alias="SMTP_USER")
    email_password: str = Field(alias="SMTP_PASSWORD")
    emails_from_name: str
    emails_from_email: str

    # URLs
    frontend_url: Optional[str] = None
    frontend_url_prod: Optional[str] = None
    frontend_url_dev: Optional[str] = None
    
    api_url: Optional[str] = None
    api_url_prod: Optional[str] = None
    api_url_dev: Optional[str] = None

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
    # Pydantic cargará automáticamente variables de entorno y .env
    settings = Settings()
    
    # 1. Resolver Database URL
    if not settings.database_url:
        if settings.environment == "production":
            # Intentar usar DATABASE_URL_PROD, o MYSQL_URL (Railway)
            settings.database_url = settings.database_url_prod or os.getenv("MYSQL_URL") or os.getenv("MYSQL_PUBLIC_URL")
        else:
            settings.database_url = settings.database_url_dev
            
    # Fix para SQLAlchemy: mysql:// -> mysql+pymysql://
    if settings.database_url and settings.database_url.startswith("mysql://"):
        settings.database_url = settings.database_url.replace("mysql://", "mysql+pymysql://")
        
    if not settings.database_url:
        # Fallback para evitar crash si no hay variable, aunque fallará al conectar
        print("WARNING: No database_url found")

    # 2. Resolver Frontend URL (para CORS)
    if not settings.frontend_url:
        if settings.environment == "production":
            settings.frontend_url = settings.frontend_url_prod
        else:
            settings.frontend_url = settings.frontend_url_dev or "http://localhost:4200"

    # 3. Resolver API URL
    if not settings.api_url:
        if settings.environment == "production":
            settings.api_url = settings.api_url_prod
        else:
            settings.api_url = settings.api_url_dev or "http://localhost:8000"

    return settings

settings = get_settings()

def is_production() -> bool:
    return settings.environment == "production"

def get_cors_origins() -> list:
    origins = []
    
    # Siempre permitir el origen configurado explícitamente
    if settings.frontend_url:
        origins.append(settings.frontend_url)
        
    # En desarrollo, agregar localhost extra por si acaso
    if not is_production():
        origins.extend([
            "http://localhost:4200",
            "http://localhost:3000",
            "http://127.0.0.1:4200",
        ])
        
    # En producción, asegurarse de que kaimox.up.railway.app esté
    if is_production():
         origins.append("https://kaimox.up.railway.app")
    
    # Eliminar duplicados
    return list(set(origins))
