"""Inicialização e gerenciamento do banco de dados."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.catalog.models import Base
from src.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    """Cria todas as tabelas."""
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Session:
    """Retorna nova sessão de banco."""
    return SessionLocal()
