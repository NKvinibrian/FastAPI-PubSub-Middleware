"""
Módulo de protocolo para logging em MongoDB.

Este módulo define o protocolo (interface) que deve ser implementado
por qualquer serviço ou repositório de logging que utilize MongoDB.

Classes:
    MongoLoggingProtocol: Protocolo para operações de logging
"""

from typing import Protocol, Union
from app.core.logging.request import RequestLog


class MongoLoggingProtocol(Protocol):
    """
    Protocolo para operações de logging em MongoDB.

    Define a interface que deve ser implementada por serviços e
    repositórios de logging, garantindo consistência na API.
    """

    async def save(self, log_data: RequestLog) -> None:
        """
        Salva um log de requisição no banco de dados.

        Args:
            log_data: Dados do log a serem persistidos
        """
        ...

    async def get_by_message_id(self, message_id: Union[str, int]) -> RequestLog | None:
        """
        Recupera um log pelo ID da mensagem.

        Args:
            message_id: ID da mensagem para busca

        Returns:
            RequestLog | None: Log encontrado ou None
        """
        ...

    async def get_by_id(self, message_id: Union[str, int]) -> RequestLog | None:
        """
        Recupera um log pelo ID do documento.

        Args:
            message_id: ID do documento para busca

        Returns:
            RequestLog | None: Log encontrado ou None
        """
        ...

    async def get_by_pub_id(self, message_id: Union[str, int]) -> RequestLog | None:
        """
        Recupera um log pelo ID de publicação.

        Args:
            message_id: ID de publicação para busca

        Returns:
            RequestLog | None: Log encontrado ou None
        """
        ...
