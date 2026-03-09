"""
Exemplo de modelo SQLAlchemy.
Este é um modelo de exemplo. Você pode criar seus próprios modelos
seguindo este padrão.
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.infrastructure.db.base import Base


class ExampleModel(Base):
    """
    Modelo de exemplo.
    Este modelo demonstra como criar uma tabela com SQLAlchemy.
    """
    __tablename__ = "example_table"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    def __repr__(self):
        return f"<ExampleModel(id={self.id}, name='{self.name}')>"
