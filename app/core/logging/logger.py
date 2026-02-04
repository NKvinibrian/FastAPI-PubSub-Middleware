from typing import Union

from app.core.logging.request import RequestLog
from app.domain.protocol.logging.mongo import MongoLoggingProtocol


class MongoLoggingService(MongoLoggingProtocol):
    def __init__(self, repository: MongoLoggingProtocol) -> None:
        self._repository = repository

    async def save(self, log_data: RequestLog) -> None:
        await self._repository.save(log_data)

    async def get_by_message_id(self, message_id: Union[str, int]) -> RequestLog | None:
        await self._repository.get_by_message_id(message_id)
