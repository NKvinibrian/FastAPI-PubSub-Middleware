"""
Aplicação FastAPI principal.

Este módulo configura e inicializa a aplicação FastAPI com middleware de logging,
roteadores de API e integração com MongoDB.

Author:
    Vinicius Maestrelli Wiggers (vi_ni_wiggers@hotmail.com)

Version:
    0.0.1
"""

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

# Instancia o serviço de logging com repositório MongoDB
logger = MongoLoggingService(
    MongoLoggingRepository(db)
)

# Adiciona middleware para logging de requisições
app.add_middleware(RequestLoggingMiddleware, logger=logger)

# Inclui os roteadores da API
app.include_router(sender.router)
app.include_router(receiver.router)
