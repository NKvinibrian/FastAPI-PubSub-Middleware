from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.logging.request import RequestLog
from app.domain.protocol.logging.mongo import MongoLoggingProtocol
from dataclasses import asdict

class MongoLoggingRepository(MongoLoggingProtocol):

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str = "logs") -> None:
        self._db = db
        self._collection = self._db[collection_name]

    async def save(self, log: RequestLog) -> None:
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
        await  self._collection.insert_one(asdict(log))

    async def get_by_message_id(self, message_id: int) -> RequestLog | None:
        document = await self._collection.find_one({"message_id": message_id})
        if document:
            return RequestLog(**document)
        return None

    async def get_by_id(self, _id: int) -> RequestLog | None:
        document = await self._collection.find_one({"id": _id})
        if document:
            return RequestLog(**document)
        return None

    async def get_by_pub_id(self, _id: int) -> RequestLog | None:
        document = await self._collection.find_one({"pub_id": _id})
        if document:
            return RequestLog(**document)
        return None
