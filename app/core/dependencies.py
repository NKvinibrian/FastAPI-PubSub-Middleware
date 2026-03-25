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

from app.infrastructure.pubsub.pubsub import PubSubPublisher
from app.domain.services.integration_example.integration import ExampleIntegrationService
from app.infrastructure.repositories.logging.mongo import MongoLoggingRepository
from app.core.logging.logger import MongoLoggingService
from app.core.config import get_settings
from app.infrastructure.vans.fetcher.graphql_fetcher import GraphQLFetcher
from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (FidelizeWholesalerFetcher,)
from app.core import mongo
from app.infrastructure.vans.connectors.graphql_connector import GraphQLConnector

# Protocol imports
from app.domain.protocol.pubsub.pubsub import PubSubProtocol
from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol
from app.domain.protocol.datasul.datasul import DatasulProtocol
from app.domain.protocol.vans.van_fetcher import VanFetcherProtocol

# NOTE: MockPubSubPublisher e MockDatasulService são importados de forma lazy
# dentro das funções que os usam, para evitar circular import (mock_pubsub importa main.py).


def get_pubsub() -> PubSubProtocol:
    """
    Retorna uma instância do serviço de publicação Pub/Sub.

    - MOCK_PUBSUB=false  → PubSubPublisher real (GCP)
    - MOCK_PUBSUB=true   → DevPubSubPublisher (leve, sem rede, para jobs em dev)

    Para testes de integração HTTP com entrega real ao endpoint FastAPI,
    use MockPubSubPublisher diretamente via override de dependência.

    Returns:
        PubSubProtocol: Implementação do protocolo de Pub/Sub
    """
    settings = get_settings()

    if settings.MOCK_PUBSUB:
        from app.infrastructure.pubsub.dev_pubsub import DevPubSubPublisher
        return DevPubSubPublisher()
    else:
        return PubSubPublisher()


def get_example_integration() -> ExampleIntegrationProtocol:
    """
    Retorna uma instância do serviço de integração de exemplo.

    Returns:
        ExampleIntegrationProtocol: Implementação do protocolo de integração
    """
    return ExampleIntegrationService()

def get_datasul_service() -> DatasulProtocol:
    from app.tests.mocks.datasul.datasul import MockDatasulService
    return MockDatasulService()  # Mock because i dont create the real service yet

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


def get_wholesaler_fetcher(auth_context):
    """
    Retorna um FidelizeWholesalerFetcher usando mock ou real.

    Se MOCK_WHOLESALER=true no .env, usa MockWholesalerConnector (dados fake, zero rede).
    Se não, usa GraphQLConnector real com auth do banco.

    Args:
        auth_context: AuthContext carregado pelo SetupContext (ignorado no mock).

    Returns:
        FidelizeWholesalerFetcher configurado.
    """


    settings = get_settings()

    if settings.MOCK_WHOLESALER:
        from app.infrastructure.vans.connectors.mock_wholesaler import MockWholesalerConnector
        connector = MockWholesalerConnector()
    else:
        connector = GraphQLConnector(auth_context=auth_context)

    graphql_fetcher = GraphQLFetcher(connector=connector)
    return FidelizeWholesalerFetcher(fetcher=graphql_fetcher)


# ═══════════════════════════════════════════════════════════════════════
#  Registry de VANs para confirm (usado pelo subscriber do Datasul)
# ═══════════════════════════════════════════════════════════════════════

# Mapeia origin_system → integration_name no banco
_VAN_REGISTRY: dict[str, str] = {
    "Fidelize Funcional Wholesaler": "Fidelize Funcional Wholesaler",
    # Adicionar novas VANs aqui:
    # "Interplayers Wholesaler": "Interplayers Wholesaler",
    # "IQVIA OL Ecommerce": "IQVIA OL Ecommerce",
}


def get_van_confirmer(origin_system: str) -> VanFetcherProtocol:
    """
    Retorna o fetcher da VAN correspondente ao origin_system.

    Usado pelo subscriber do Datasul para confirmar pedidos
    como importados na VAN de origem após aceite.

    Args:
        origin_system: Nome do sistema de origem (vem do PubSub attributes).

    Returns:
        VanFetcherProtocol configurado para a VAN.

    Raises:
        ValueError: Se o origin_system não está registrado.
    """
    integration_name = _VAN_REGISTRY.get(origin_system)
    if not integration_name:
        raise ValueError(
            f"VAN desconhecida para confirm: '{origin_system}'. "
            f"Registre em _VAN_REGISTRY no dependencies.py."
        )

    from app.infrastructure.db import SessionLocal
    from app.infrastructure.vans.auth.setup_contex import SetupContext

    db = SessionLocal()
    setup = SetupContext(db=db)
    van_context = setup.load(integration_name)

    return get_wholesaler_fetcher(auth_context=van_context.auth)


