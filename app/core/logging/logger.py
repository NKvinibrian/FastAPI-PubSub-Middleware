"""
Módulo de serviço de logging.

Este módulo implementa o serviço de logging que atua como uma camada
intermediária entre o middleware e o repositório de dados.

Classes:
    MongoLoggingService: Serviço de logging que implementa MongoLoggingProtocol
"""

from typing import Union

from app.core.logging.request import RequestLog
from app.domain.protocol.logging.mongo import MongoLoggingProtocol


class MongoLoggingService(MongoLoggingProtocol):
    """
    Serviço de logging com persistência em MongoDB.

    Esta classe implementa o protocolo MongoLoggingProtocol e delega
    as operações de persistência para um repositório.

    Attributes:
        _repository: Instância do repositório de logging
    """

    def __init__(self, repository: MongoLoggingProtocol) -> None:
        """
        Inicializa o serviço de logging.

        Args:
            repository: Repositório que implementa MongoLoggingProtocol
        """
        self._repository = repository

    async def save(self, log_data: RequestLog) -> None:
        """
        Salva um log de requisição.

        Args:
            log_data: Dados do log a serem salvos
        """
        await self._repository.save(log_data)

    async def get_by_message_id(self, message_id: Union[str, int]) -> RequestLog | None:
        """
        Recupera um log pelo ID da mensagem.

        Args:
            message_id: ID da mensagem para busca

        Returns:
            RequestLog | None: Log encontrado ou None se não existir
        """
        await self._repository.get_by_message_id(message_id)
