"""
Helper de logging para integrações de VANs.

Facilita a criação de registros de IntegrationLog para cada etapa
do pipeline (fetcher, parser, pubsub, confirm), mantendo o código DRY.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from app.domain.entities.logs.integrations import IntegrationLogEntity
from app.domain.protocol.logs.integration_log_repository import IntegrationLogRepositoryProtocol


class IntegrationLogger:
    """
    Utilitário para registrar logs de integração.

    Encapsula a criação e persistência de IntegrationLogEntity,
    gerenciando timestamps de início/fim e cálculo de duração.

    Attributes:
        _repository: Repositório de IntegrationLog.
        _origin_system: Nome do sistema de origem (ex: Fidelize Funcional Wholesaler).
        _log_uuid: UUID do grupo de processamento.
    """

    def __init__(
        self,
        repository: IntegrationLogRepositoryProtocol,
        origin_system: str,
        log_uuid: UUID,
    ) -> None:
        self._repository = repository
        self._origin_system = origin_system
        self._log_uuid = log_uuid

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Se o datetime for naive, assume UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _calc_duration_ms(self, started_at: datetime, finished_at: datetime) -> int:
        delta = self._ensure_aware(finished_at) - self._ensure_aware(started_at)
        return int(delta.total_seconds() * 1000)

    def start(
        self,
        component_name: str,
        process_name: str,
        message_text: Optional[str] = None,
    ) -> IntegrationLogEntity:
        """
        Registra o início de uma etapa do pipeline.

        Args:
            component_name: Nome do componente (fetcher, parser, pubsub, confirm).
            process_name: Nome do processo/classe executando.
            message_text: Mensagem descritiva opcional.

        Returns:
            IntegrationLogEntity persistida com status STARTED.
        """
        now = self._now()
        entity = IntegrationLogEntity(
            log_uuid=self._log_uuid,
            origin_system=self._origin_system,
            component_name=component_name,
            process_name=process_name,
            message_text=message_text,
            created_at=now,
            started_at=now,
            status="STARTED",
        )
        return self._repository.create(entity)

    def success(
        self,
        log: IntegrationLogEntity,
        message_text: Optional[str] = None,
        response_json: Optional[dict[str, Any]] = None,
    ) -> IntegrationLogEntity:
        """
        Marca uma etapa como concluída com sucesso.

        Args:
            log: Entidade de log retornada por start().
            message_text: Mensagem de conclusão opcional.
            response_json: JSON de resposta opcional.

        Returns:
            IntegrationLogEntity atualizada com status SUCCESS.
        """
        now = self._now()
        log.status = "SUCCESS"
        log.finished_at = now
        log.updated_at = now
        if message_text:
            log.message_text = message_text
        if response_json:
            log.response_json = response_json
        if log.started_at:
            log.duration_ms = self._calc_duration_ms(log.started_at, now)
        return self._repository.update(log)

    def fail(
        self,
        log: IntegrationLogEntity,
        error_details: str,
        message_text: Optional[str] = None,
    ) -> IntegrationLogEntity:
        """
        Marca uma etapa como falha.

        Args:
            log: Entidade de log retornada por start().
            error_details: Descrição do erro.
            message_text: Mensagem adicional opcional.

        Returns:
            IntegrationLogEntity atualizada com status FAILED.
        """
        now = self._now()
        log.status = "FAILED"
        log.finished_at = now
        log.updated_at = now
        log.error_details = error_details
        if message_text:
            log.message_text = message_text
        if log.started_at:
            log.duration_ms = self._calc_duration_ms(log.started_at, now)
        return self._repository.update(log)

