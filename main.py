from fastapi import FastAPI
from app.api.v1.routes.api_pub import sender
from app.api.v1.routes.api_sub import receiver
from app.core.logging.middleware import RequestLoggingMiddleware
from app.core.logging.logger import MongoLoggingService
from app.core.mongo import db
from app.infrastructure.repositories.logging.mongo import MongoLoggingRepository

app = FastAPI(
    title="Vina Examples",
    version="0.0.1",
    contact={
        "name": "Vinicius Maestrelli Wiggers",
        "email": "vi_ni_wiggers@hotmail.com"
    },
)

# Instacia o do middleware de logging
logger = MongoLoggingService(
    MongoLoggingRepository(db)
)

app.add_middleware(RequestLoggingMiddleware, logger=logger)

app.include_router(sender.router)
app.include_router(receiver.router)
