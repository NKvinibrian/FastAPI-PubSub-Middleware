"""
Repositório de LogPrePedidosVans.

Implementa operações CRUD para o modelo LogPrePedidosVansModels
utilizando uma sessão SQLAlchemy síncrona.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

# Entity
from app.domain.entities.logs.vans import LogPrePedidosVansEntity

# Model
from app.infrastructure.db.models.logging.vans import LogPrePedidosVansModels

# Protocol
from app.domain.protocol.logs.repository import LogPrePedidosVansRepositoryProtocol


class LogPrePedidosVansRepository(LogPrePedidosVansRepositoryProtocol):
    """
    Repositório para persistência de LogPrePedidosVans no PostgreSQL.

    Attributes:
        _db: Sessão ativa do SQLAlchemy.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def __map_to_entity(log: LogPrePedidosVansModels) -> LogPrePedidosVansEntity:
        return LogPrePedidosVansEntity(
            id=log.id,
            pedido_van_id=log.pedido_van_id,
            message_id=log.message_id,
            log_uuid=log.log_uuid,
            integration_id=log.integration_id,
            integration_status=log.integration_status,
        )

    def get_all(self) -> list[LogPrePedidosVansEntity]:
        results = self._db.scalars(select(LogPrePedidosVansModels)).all()
        return [self.__map_to_entity(item) for item in results]

    def get_by_id(self, log_id: int) -> Optional[LogPrePedidosVansEntity]:
        result = self._db.scalars(
            select(LogPrePedidosVansModels).where(LogPrePedidosVansModels.id == log_id)
        ).first()
        if result is None:
            return None
        return self.__map_to_entity(result)

    def get_by_pedido_van_id(self, pedido_van_id: str) -> list[LogPrePedidosVansEntity]:
        results = self._db.scalars(
            select(LogPrePedidosVansModels).where(
                LogPrePedidosVansModels.pedido_van_id == pedido_van_id
            )
        ).all()
        return [self.__map_to_entity(item) for item in results]

    def get_by_message_id(self, message_id: int) -> Optional[LogPrePedidosVansEntity]:
        result = self._db.scalars(
            select(LogPrePedidosVansModels).where(
                LogPrePedidosVansModels.message_id == message_id
            )
        ).first()
        if result is None:
            return None
        return self.__map_to_entity(result)

    def create(self, log: LogPrePedidosVansEntity) -> LogPrePedidosVansEntity:
        db_log = LogPrePedidosVansModels(
            pedido_van_id=log.pedido_van_id,
            message_id=log.message_id,
            log_uuid=log.log_uuid,
            integration_id=log.integration_id,
            integration_status=log.integration_status,
        )
        self._db.add(db_log)
        self._db.commit()
        self._db.refresh(db_log)
        return self.__map_to_entity(db_log)

    def update(self, log: LogPrePedidosVansEntity) -> LogPrePedidosVansEntity:
        result = self._db.scalars(
            select(LogPrePedidosVansModels).where(LogPrePedidosVansModels.id == log.id)
        ).first()
        if result is None:
            raise ValueError(f"LogPrePedidosVans with id={log.id} not found.")
        result.pedido_van_id = log.pedido_van_id
        result.message_id = log.message_id
        result.log_uuid = log.log_uuid
        result.integration_id = log.integration_id
        result.integration_status = log.integration_status
        self._db.commit()
        self._db.refresh(result)
        return self.__map_to_entity(result)

    def delete(self, log_id: int) -> None:
        result = self._db.scalars(
            select(LogPrePedidosVansModels).where(LogPrePedidosVansModels.id == log_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()

