from typing import Protocol, Union
from app.core.logging.request import RequestLog


class MongoLoggingProtocol(Protocol):

    async def save(self, log_data: RequestLog) -> None:
        ...

    async def get_by_message_id(self, message_id: Union[str, int]) -> RequestLog | None:
        ...

    async def get_by_id(self, message_id: Union[str, int]) -> RequestLog | None:
        ...

    async def get_by_pub_id(self, message_id: Union[str, int]) -> RequestLog | None:
        ...
