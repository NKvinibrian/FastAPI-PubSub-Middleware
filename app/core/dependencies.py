"""
Módulo de injeção de dependências.

Este módulo centraliza as funções de factory para injeção de dependências
do FastAPI, fornecendo instâncias de serviços, repositórios e integrações.

Funções:
    get_pubsub: Retorna uma instância do serviço de Pub/Sub
    get_example_integration: Retorna uma instância do serviço de integração de exemplo
    get_logging_repository: Retorna uma instância do repositório de logging
    get_logging_service: Retorna uma instância do serviço de logging
"""

from app.domain.protocol.pubsub.pubsub import PubSubProtocol
from app.infrastructure.pubsub.pubsub import PubSubPublisher

from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol
from app.domain.services.integration_example.integration import ExampleIntegrationService

from app.infrastructure.repositories.logging.mongo import MongoLoggingRepository
from app.core.logging.logger import MongoLoggingService

from app.core import mongo


def get_pubsub() -> PubSubProtocol:
    """
    Retorna uma instância do serviço de publicação Pub/Sub.

    Returns:
        PubSubProtocol: Implementação do protocolo de Pub/Sub
    """
    return PubSubPublisher()


def get_example_integration() -> ExampleIntegrationProtocol:
    """
    Retorna uma instância do serviço de integração de exemplo.

    Returns:
        ExampleIntegrationProtocol: Implementação do protocolo de integração
    """
    return ExampleIntegrationService()


def get_logging_repository():
    """
    Retorna uma instância do repositório de logging MongoDB.

    Returns:
        MongoLoggingRepository: Repositório configurado para a collection 'logs'
    """
    return MongoLoggingRepository(mongo.db, collection_name="logs")


def get_logging_service():
    """
    Retorna uma instância do serviço de logging.

    Returns:
        MongoLoggingService: Serviço de logging configurado com repositório MongoDB
    """
    logging_repository = get_logging_repository()
    return MongoLoggingService(logging_repository)
