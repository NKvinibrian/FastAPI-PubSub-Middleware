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
from app.infrastructure.vans.operations_loader import OperationConfig
from app.core import mongo
from app.infrastructure.vans.connectors.graphql_connector import GraphQLConnector

# Protocol imports
from app.domain.protocol.pubsub.pubsub import PubSubProtocol
from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol
from app.domain.protocol.datasul.datasul import DatasulProtocol
from app.domain.protocol.vans.van_fetcher import VanFetcherProtocol
from app.domain.protocol.vans.backup_storage import VanBackupStorageProtocol
from app.domain.services.vans.observer_subscriber_service import ObserverSubscriberService

# NOTE: MockPubSubPublisher e MockDatasulService são importados de forma lazy
# dentro das funções que os usam, para evitar circular import (mock_pubsub importa main.py).


def get_pubsub() -> PubSubProtocol:
    """
    Retorna uma instância do serviço de publicação Pub/Sub.

    - MOCK_PUBSUB=false  → PubSubPublisher real (GCP)
    - MOCK_PUBSUB=true   → MockPubSubPublisher (entrega via HTTP aos subscribers locais)

    Returns:
        PubSubProtocol: Implementação do protocolo de Pub/Sub
    """
    settings = get_settings()

    if settings.MOCK_PUBSUB:
        from app.tests.mocks.pubsub.mock_pubsub import MockPubSubPublisher
        return MockPubSubPublisher()
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
    """
    Retorna uma instância do serviço Datasul.

    - MOCK_DATASUL=false → DatasulService real
    - MOCK_DATASUL=true  → MockDatasulService (simula aceite e persiste pedidos mock no banco)

    Returns:
        DatasulProtocol: Implementação do protocolo Datasul
    """
    settings = get_settings()

    if settings.MOCK_DATASUL:
        from app.tests.mocks.datasul.datasul import MockDatasulService
        return MockDatasulService()
    else:
        from app.infrastructure.datasul.datasul_service import DatasulService
        return DatasulService()

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


def get_wholesaler_fetcher(auth_context, operations: dict[str, OperationConfig] | None = None):
    """
    Retorna um FidelizeWholesalerFetcher usando mock ou real.

    Se MOCK_WHOLESALER=true no .env, usa MockWholesalerConnector (dados fake, zero rede).
    Se não, usa GraphQLConnector real com auth do banco.

    Args:
        auth_context: AuthContext carregado pelo SetupContext (ignorado no mock).
        operations: Mapa nome → OperationConfig vindo de hub.request_details.
            Quando None, o fetcher usa o comportamento legado (URL do auth_context).

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
    return FidelizeWholesalerFetcher(fetcher=graphql_fetcher, operations=operations)


def get_van_backup(integration_name: str) -> VanBackupStorageProtocol:
    """
    Retorna o backup storage usado pelo VanPipeline.

    - MOCK_GCS_BACKUP=true → MockBackupStorage (in-memory, padrão dev/test).
    - MOCK_GCS_BACKUP=false → GCSBackupStorage real, gravando no bucket
      configurado em GCS_BACKUP_BUCKET.

    base_path no bucket = nome da integração (mesmo padrão do legado).

    Args:
        integration_name: Nome da integração (vira `<bucket>/<integration_name>/...`).

    Returns:
        Implementação de VanBackupStorageProtocol.
    """
    settings = get_settings()

    if settings.MOCK_GCS_BACKUP:
        from app.tests.mocks.vans.mock_backup_storage import MockBackupStorage
        return MockBackupStorage(
            bucket_name=settings.GCS_BACKUP_BUCKET,
            base_path=integration_name,
        )

    from app.infrastructure.vans.backup.gcs_backup_storage import GCSBackupStorage

    credentials_json: str | None = None
    if settings.GCP_CREDENTIALS_PATH:
        try:
            with open(settings.GCP_CREDENTIALS_PATH, "r") as fp:
                credentials_json = fp.read()
        except OSError:
            credentials_json = None

    return GCSBackupStorage(
        bucket_name=settings.GCS_BACKUP_BUCKET,
        base_path=integration_name,
        service_account_json=credentials_json,
    )


def get_observer_subscriber_service(db, httpx_transport=None):
    """
    Retorna o service do Observer Subscriber.

    - MOCK_OBSERVER_VAN=false → ObserverSubscriberService real (envia HTTP à VAN)
    - MOCK_OBSERVER_VAN=true  → MockObserverSubscriberService (simula envio, marca flags no DB)

    Args:
        db: Sessão SQLAlchemy.
        httpx_transport: Transport HTTP (usado no service real; ignorado no mock).

    Returns:
        ObserverSubscriberService ou MockObserverSubscriberService.
    """
    settings = get_settings()

    if settings.MOCK_OBSERVER_VAN:
        from app.tests.mocks.vans.mock_observer_subscriber import MockObserverSubscriberService
        return MockObserverSubscriberService(db=db)
    else:
        return ObserverSubscriberService(db=db, httpx_transport=httpx_transport)


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
    from app.infrastructure.vans.operations_loader import load_operations
    from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (
        OPERATION_GET_PRE_ORDERS,
        OPERATION_SET_ORDERS_AS_IMPORTED,
    )

    db = SessionLocal()
    setup = SetupContext(db=db)
    van_context = setup.load(integration_name)

    operations = load_operations(
        db=db,
        integration_id=van_context.integration_id,
        base_url=van_context.auth.base_url,
        operation_names=[OPERATION_GET_PRE_ORDERS, OPERATION_SET_ORDERS_AS_IMPORTED],
    )

    return get_wholesaler_fetcher(auth_context=van_context.auth, operations=operations)


