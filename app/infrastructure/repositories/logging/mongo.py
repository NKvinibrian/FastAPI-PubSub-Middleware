"""
Módulo de repositório de logging em MongoDB.

Este módulo implementa o repositório de dados para persistência de logs
de requisições HTTP em MongoDB, seguindo o MongoLoggingProtocol.

Classes:
    MongoLoggingRepository: Repositório para operações de logging em MongoDB
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.logging.request import RequestLog
from app.domain.protocol.logging.mongo import MongoLoggingProtocol
from dataclasses import asdict


class MongoLoggingRepository(MongoLoggingProtocol):
    """
    Repositório para persistência de logs em MongoDB.

    Esta classe implementa todas as operações de acesso a dados
    relacionadas ao logging de requisições.

    Attributes:
        _db: Instância do banco de dados MongoDB
        _collection: Collection do MongoDB para armazenar os logs
    """

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str = "logs") -> None:
        """
        Inicializa o repositório de logging.

        Args:
            db: Instância do banco de dados MongoDB
            collection_name: Nome da collection para armazenar logs (padrão: "logs")
        """
        self._db = db
        self._collection = self._db[collection_name]

    async def save(self, log: RequestLog) -> None:
        """
        Salva um log de requisição no MongoDB.

        Converte o dataclass RequestLog para dicionário e insere no banco.

        Args:
            log: Objeto RequestLog com os dados a serem salvos
        """
        # await self._collection.insert_one({
        #     "message_id": log.message_id,
        #     "pub_id": log.pub_id,
        #     "log_data": {
        #         "method": log.method,
        #         "path": log.path,
        #         "status_code": log.status_code,
        #         "success": log.success,
        #         "duration_ms": log.duration_ms,
        #         "error_type": log.error_type,
        #         "error_message": log.error_message,
        #     }
        # })
        await self._collection.insert_one(asdict(log))

    async def get_by_message_id(self, message_id: int) -> RequestLog | None:
        """
        Busca um log pelo ID da mensagem.

        Args:
            message_id: ID da mensagem para busca

        Returns:
            RequestLog | None: Log encontrado ou None se não existir
        """
        document = await self._collection.find_one({"message_id": message_id})
        if document:
            return RequestLog(**document)
        return None

    async def get_by_id(self, _id: int) -> RequestLog | None:
        """
        Busca um log pelo ID do documento.

        Args:
            _id: ID do documento para busca

        Returns:
            RequestLog | None: Log encontrado ou None se não existir
        """
        document = await self._collection.find_one({"id": _id})
        if document:
            return RequestLog(**document)
        return None

    async def get_by_pub_id(self, _id: int) -> RequestLog | None:
        """
        Busca um log pelo ID de publicação.

        Args:
            _id: ID de publicação para busca

        Returns:
            RequestLog | None: Log encontrado ou None se não existir
        """
        document = await self._collection.find_one({"pub_id": _id})
        if document:
            return RequestLog(**document)
        return None
