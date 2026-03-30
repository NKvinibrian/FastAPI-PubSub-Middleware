"""
Repositórios de ProjetoSiglas, OrigemSistemas e ProjetoSiglaOrigem.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.vans.configuracao import (
    ProjetoSiglasEntity,
    OrigemSistemasEntity,
    ProjetoSiglaOrigemEntity,
)
from app.infrastructure.db.models.vans.configuracao import (
    ProjetoSiglas,
    OrigemSistemas,
    ProjetoSiglaOrigem,
)
from app.domain.protocol.vans.configuracao_repository import (
    ProjetoSiglasRepositoryProtocol,
    OrigemSistemasRepositoryProtocol,
    ProjetoSiglaOrigemRepositoryProtocol,
)


# ═══════════════════════════════════════════════════════════════════════
#  ProjetoSiglasRepository
# ═══════════════════════════════════════════════════════════════════════

class ProjetoSiglasRepository(ProjetoSiglasRepositoryProtocol):
    """Repositório para persistência de ProjetoSiglas no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: ProjetoSiglas) -> ProjetoSiglasEntity:
        return ProjetoSiglasEntity(
            id=m.id,
            projeto_sigla=m.projeto_sigla,
            descricao_industria=m.descricao_industria,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[ProjetoSiglasEntity]:
        results = self._db.scalars(select(ProjetoSiglas)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, projeto_id: int) -> Optional[ProjetoSiglasEntity]:
        result = self._db.scalars(
            select(ProjetoSiglas).where(ProjetoSiglas.id == projeto_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_sigla(self, projeto_sigla: str) -> Optional[ProjetoSiglasEntity]:
        result = self._db.scalars(
            select(ProjetoSiglas).where(ProjetoSiglas.projeto_sigla == projeto_sigla)
        ).first()
        return self._map_to_entity(result) if result else None

    def create(self, projeto: ProjetoSiglasEntity) -> ProjetoSiglasEntity:
        db_obj = ProjetoSiglas(
            projeto_sigla=projeto.projeto_sigla,
            descricao_industria=projeto.descricao_industria,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, projeto: ProjetoSiglasEntity) -> ProjetoSiglasEntity:
        result = self._db.scalars(
            select(ProjetoSiglas).where(ProjetoSiglas.id == projeto.id)
        ).first()
        if result is None:
            raise ValueError(f"ProjetoSiglas with id={projeto.id} not found.")
        result.projeto_sigla = projeto.projeto_sigla
        result.descricao_industria = projeto.descricao_industria
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, projeto_id: int) -> None:
        result = self._db.scalars(
            select(ProjetoSiglas).where(ProjetoSiglas.id == projeto_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  OrigemSistemasRepository
# ═══════════════════════════════════════════════════════════════════════

class OrigemSistemasRepository(OrigemSistemasRepositoryProtocol):
    """Repositório para persistência de OrigemSistemas no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: OrigemSistemas) -> OrigemSistemasEntity:
        return OrigemSistemasEntity(
            id=m.id,
            origem_sistema=m.origem_sistema,
            descricao=m.descricao,
            observacao=m.observacao,
            is_pbm=m.is_pbm,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[OrigemSistemasEntity]:
        results = self._db.scalars(select(OrigemSistemas)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, origem_id: int) -> Optional[OrigemSistemasEntity]:
        result = self._db.scalars(
            select(OrigemSistemas).where(OrigemSistemas.id == origem_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_origem_sistema(self, origem_sistema: str) -> Optional[OrigemSistemasEntity]:
        result = self._db.scalars(
            select(OrigemSistemas).where(OrigemSistemas.origem_sistema == origem_sistema)
        ).first()
        return self._map_to_entity(result) if result else None

    def create(self, origem: OrigemSistemasEntity) -> OrigemSistemasEntity:
        db_obj = OrigemSistemas(
            origem_sistema=origem.origem_sistema,
            descricao=origem.descricao,
            observacao=origem.observacao,
            is_pbm=origem.is_pbm,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, origem: OrigemSistemasEntity) -> OrigemSistemasEntity:
        result = self._db.scalars(
            select(OrigemSistemas).where(OrigemSistemas.id == origem.id)
        ).first()
        if result is None:
            raise ValueError(f"OrigemSistemas with id={origem.id} not found.")
        result.origem_sistema = origem.origem_sistema
        result.descricao = origem.descricao
        result.observacao = origem.observacao
        result.is_pbm = origem.is_pbm
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, origem_id: int) -> None:
        result = self._db.scalars(
            select(OrigemSistemas).where(OrigemSistemas.id == origem_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  ProjetoSiglaOrigemRepository
# ═══════════════════════════════════════════════════════════════════════

class ProjetoSiglaOrigemRepository(ProjetoSiglaOrigemRepositoryProtocol):
    """Repositório para persistência de ProjetoSiglaOrigem no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: ProjetoSiglaOrigem) -> ProjetoSiglaOrigemEntity:
        return ProjetoSiglaOrigemEntity(
            id=m.id,
            projeto_sigla_id=m.projeto_sigla_id,
            origem_sistema_id=m.origem_sistema_id,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[ProjetoSiglaOrigemEntity]:
        results = self._db.scalars(select(ProjetoSiglaOrigem)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, vinculo_id: int) -> Optional[ProjetoSiglaOrigemEntity]:
        result = self._db.scalars(
            select(ProjetoSiglaOrigem).where(ProjetoSiglaOrigem.id == vinculo_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_projeto_sigla_id(self, projeto_sigla_id: int) -> list[ProjetoSiglaOrigemEntity]:
        results = self._db.scalars(
            select(ProjetoSiglaOrigem).where(
                ProjetoSiglaOrigem.projeto_sigla_id == projeto_sigla_id
            )
        ).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_origem_sistema_id(self, origem_sistema_id: int) -> list[ProjetoSiglaOrigemEntity]:
        results = self._db.scalars(
            select(ProjetoSiglaOrigem).where(
                ProjetoSiglaOrigem.origem_sistema_id == origem_sistema_id
            )
        ).all()
        return [self._map_to_entity(r) for r in results]

    def create(self, vinculo: ProjetoSiglaOrigemEntity) -> ProjetoSiglaOrigemEntity:
        db_obj = ProjetoSiglaOrigem(
            projeto_sigla_id=vinculo.projeto_sigla_id,
            origem_sistema_id=vinculo.origem_sistema_id,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, vinculo: ProjetoSiglaOrigemEntity) -> ProjetoSiglaOrigemEntity:
        result = self._db.scalars(
            select(ProjetoSiglaOrigem).where(ProjetoSiglaOrigem.id == vinculo.id)
        ).first()
        if result is None:
            raise ValueError(f"ProjetoSiglaOrigem with id={vinculo.id} not found.")
        result.projeto_sigla_id = vinculo.projeto_sigla_id
        result.origem_sistema_id = vinculo.origem_sistema_id
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, vinculo_id: int) -> None:
        result = self._db.scalars(
            select(ProjetoSiglaOrigem).where(ProjetoSiglaOrigem.id == vinculo_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()
