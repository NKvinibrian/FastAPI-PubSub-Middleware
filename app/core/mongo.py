"""
Módulo de conexão com MongoDB.

Este módulo configura a conexão com o banco de dados MongoDB utilizando
Motor (driver assíncrono) e disponibiliza a instância do banco de dados
para uso em toda a aplicação.

Variáveis:
    settings: Configurações da aplicação
    client: Cliente AsyncIOMotorClient para conexão com MongoDB
    db: Instância do banco de dados MongoDB
"""

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings

# Carrega as configurações
settings = get_settings()

# Cria o cliente MongoDB assíncrono
client = AsyncIOMotorClient(settings.MONGO_URI)

# Seleciona o banco de dados
db = client[settings.MONGO_DB_NAME]
