from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Crear el engine usando la URL de settings (detecta local o producción)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Evita que se caiga la conexión por inactividad
    pool_recycle=3600,   # Recicla conexiones cada hora
    connect_args={}       # Para MySQL no necesita argumentos adicionales en local
)

# Crear la sesión de base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Dependencia para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
