import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# DATABASE_USER = os.environ.get("MYSQLUSER", "root")
# DATABASE_PASSWORD = os.environ.get("MYSQLPASSWORD", "chAVuwbfFRQeTppuvhpbMhkVGfkBqvqZ")
# DATABASE_HOST = os.environ.get("MYSQLHOST", "mysql.railway.internal")
# DATABASE_PORT = os.environ.get("MYSQLPORT", "3306")
# DATABASE_NAME = os.environ.get("MYSQLDATABASE", "railway")

# SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()