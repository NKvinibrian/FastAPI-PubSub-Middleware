"""
Base para os modelos do SQLAlchemy.

Este módulo define a classe base para todos os modelos de banco de dados
e fornece a engine e session do SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import get_settings

settings = get_settings()

# Criar a engine do SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)

# Criar a SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criar a classe base para os modelos
Base = declarative_base()


def get_db():
    """
    Dependency para obter uma sessão do banco de dados.

    Yields:
        Session: Sessão do SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

