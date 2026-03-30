from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from app.infrastructure.db import Base


class ProjetoSiglas(Base, DefaultAttributesModel):
    __tablename__ = "vans_projeto_siglas"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    projeto_sigla = Column(String(255), nullable=False, unique=True, comment="Ex: LIB, SAN, RCH")
    descricao_industria = Column(String(255), nullable=True, comment="Ex: Libbs / Roche / Sanofi")

    projeto_origem_links = relationship("ProjetoSiglaOrigem", back_populates="projeto")


class OrigemSistemas(Base, DefaultAttributesModel):
    __tablename__ = "vans_origem_sistemas"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    origem_sistema = Column(String(255), nullable=False, unique=True, comment="Ex: Funcional")
    descricao = Column(String(255))
    observacao = Column(String(255))
    is_pbm = Column(Boolean, default=False, nullable=False)

    projeto_origem_links = relationship("ProjetoSiglaOrigem", back_populates="origem")


class ProjetoSiglaOrigem(Base, DefaultAttributesModel):
    __tablename__ = "vans_projeto_sigla_origem"
    __table_args__ = (
        UniqueConstraint("projeto_sigla_id", "origem_sistema_id", name="uq_projeto_origem"),
        {"schema": "hub"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    projeto_sigla_id = Column(Integer, ForeignKey("hub.vans_projeto_siglas.id"), nullable=False)
    origem_sistema_id = Column(Integer, ForeignKey("hub.vans_origem_sistemas.id"), nullable=False)

    projeto = relationship("ProjetoSiglas", back_populates="projeto_origem_links")
    origem = relationship("OrigemSistemas", back_populates="projeto_origem_links")