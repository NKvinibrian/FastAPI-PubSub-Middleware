"""
Repositório de IntegrationLogs.

Implementa operações CRUD para o modelo IntegrationLogs
utilizando uma sessão SQLAlchemy síncrona.

O delete é soft — apenas altera o status para 'DELETED'.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

# Entity
from app.domain.entities.logs.integrations import IntegrationLogEntity

# Model
from app.infrastructure.db.models.logging.integrations import IntegrationLogs

# Protocol
from app.domain.protocol.logs.integration_log_repository import IntegrationLogRepositoryProtocol


class IntegrationLogRepository(IntegrationLogRepositoryProtocol):
    """
    Repositório para persistência de IntegrationLogs no PostgreSQL.

    Attributes:
        _db: Sessão ativa do SQLAlchemy.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(log: IntegrationLogs) -> IntegrationLogEntity:
        """Converte um model SQLAlchemy para entity de domínio."""
        return IntegrationLogEntity(
            id=log.id,
            log_uuid=log.log_uuid,
            origin_system=log.origin_system,
            component_name=log.component_name,
            process_name=log.process_name,
            message_text=log.message_text,
            file_path=log.file_path,
            response_json=log.response_json,
            file_type=log.file_type,
            error_details=log.error_details,
            created_at=log.created_at,
            started_at=log.started_at,
            finished_at=log.finished_at,
            duration_ms=log.duration_ms,
            updated_at=log.updated_at,
            status=log.status,
        )

    @staticmethod
    def _map_to_model(entity: IntegrationLogEntity) -> IntegrationLogs:
        """Converte uma entity de domínio para model SQLAlchemy (sem id)."""
        return IntegrationLogs(
            log_uuid=entity.log_uuid,
            origin_system=entity.origin_system,
            component_name=entity.component_name,
            process_name=entity.process_name,
            message_text=entity.message_text,
            file_path=entity.file_path,
            response_json=entity.response_json,
            file_type=entity.file_type,
            error_details=entity.error_details,
            created_at=entity.created_at,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            duration_ms=entity.duration_ms,
            updated_at=entity.updated_at,
            status=entity.status,
        )

    def get_all(self) -> list[IntegrationLogEntity]:
        """Retorna todos os logs de integração."""
        results = self._db.scalars(select(IntegrationLogs)).all()
        return [self._map_to_entity(item) for item in results]

    def get_by_id(self, log_id: int) -> Optional[IntegrationLogEntity]:
        """Busca um log pelo ID."""
        result = self._db.scalars(
            select(IntegrationLogs).where(IntegrationLogs.id == log_id)
        ).first()
        if result is None:
            return None
        return self._map_to_entity(result)

    def get_by_log_uuid(self, log_uuid: UUID) -> list[IntegrationLogEntity]:
        """Busca todos os logs de um grupo de processamento (log_uuid)."""
        results = self._db.scalars(
            select(IntegrationLogs).where(IntegrationLogs.log_uuid == log_uuid)
        ).all()
        return [self._map_to_entity(item) for item in results]

    def get_by_origin_system(self, origin_system: str) -> list[IntegrationLogEntity]:
        """Busca logs pelo sistema de origem."""
        results = self._db.scalars(
            select(IntegrationLogs).where(
                IntegrationLogs.origin_system == origin_system
            )
        ).all()
        return [self._map_to_entity(item) for item in results]

    def get_by_status(self, status: str) -> list[IntegrationLogEntity]:
        """Busca logs pelo status."""
        results = self._db.scalars(
            select(IntegrationLogs).where(IntegrationLogs.status == status)
        ).all()
        return [self._map_to_entity(item) for item in results]

    def create(self, log: IntegrationLogEntity) -> IntegrationLogEntity:
        """Cria um novo log de integração."""
        db_log = self._map_to_model(log)
        self._db.add(db_log)
        self._db.commit()
        self._db.refresh(db_log)
        return self._map_to_entity(db_log)

    def update(self, log: IntegrationLogEntity) -> IntegrationLogEntity:
        """Atualiza um log de integração existente."""
        result = self._db.scalars(
            select(IntegrationLogs).where(IntegrationLogs.id == log.id)
        ).first()

        if result is None:
            raise ValueError(f"IntegrationLog with id={log.id} not found.")

        result.log_uuid = log.log_uuid
        result.origin_system = log.origin_system
        result.component_name = log.component_name
        result.process_name = log.process_name
        result.message_text = log.message_text
        result.file_path = log.file_path
        result.response_json = log.response_json
        result.file_type = log.file_type
        result.error_details = log.error_details
        result.created_at = log.created_at
        result.started_at = log.started_at
        result.finished_at = log.finished_at
        result.duration_ms = log.duration_ms
        result.updated_at = log.updated_at
        result.status = log.status

        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, log_id: int) -> None:
        """Soft delete — altera o status para 'DELETED'."""
        result = self._db.scalars(
            select(IntegrationLogs).where(IntegrationLogs.id == log_id)
        ).first()
        if result is not None:
            result.status = "DELETED"
            self._db.commit()

