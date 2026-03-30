"""
Job de orquestração: Fidelize Funcional Wholesaler — Observer.

Fluxo reverso delegado à ObserverPipeline genérica:
    Query DB → Parse → Publish (para os 4 fluxos)

Os 4 tópicos PubSub:
  - merco-observer-order-return
  - merco-observer-order-rejection
  - merco-observer-invoices
  - merco-observer-cancellation

Cada mensagem é genérica (ObserverMessageSchema) e o subscriber
da VAN consome e chama a API específica.
"""


import asyncio
import logging
from uuid import uuid4, UUID

from app.infrastructure.db import SessionLocal

# Setup / Auth
from app.infrastructure.vans.auth.setup_contex import SetupContext

# Pipeline
from app.pipelines.vans.observer_pipeline import ObserverPipeline

# Parser
from app.domain.services.vans.fidelize_observer_parser import FidelizeObserverParser

# PubSub
from app.api.v1.schemas.vans.observer_message import ObserverAction
from app.infrastructure.vans.pubsub.observer_publisher import ObserverPubSubPublisher
from app.core.dependencies import get_pubsub

# Repositories
from app.infrastructure.repositories.logging.integrations import IntegrationLogRepository

# Logger helper
from app.domain.services.vans.integration_logger import IntegrationLogger

# Print logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "Fidelize Funcional Wholesaler"

OBSERVER_TOPICS: dict[ObserverAction, str] = {
    ObserverAction.ORDER_RETURN: "merco-observer-order-return",
    ObserverAction.ORDER_RETURN_REJECTION: "merco-observer-order-rejection",
    ObserverAction.RETURN_INVOICES: "merco-observer-invoices",
    ObserverAction.RETURN_CANCELLATION: "merco-observer-cancellation",
}


async def run() -> None:
    """
    Monta os componentes e delega a execução à ObserverPipeline genérica.
    """
    db = SessionLocal()
    log_uuid: UUID = uuid4()

    logger.info("═" * 60)
    logger.info("JOB: %s — Observer", INTEGRATION_NAME)
    logger.info("log_uuid: %s", log_uuid)
    logger.info("═" * 60)

    try:
        # ── Setup ──────────────────────────────────────────────────────
        setup = SetupContext(db=db)
        van_context = setup.load(INTEGRATION_NAME)

        # ── Componentes ────────────────────────────────────────────────
        integration_log_repo = IntegrationLogRepository(db=db)

        integration_logger = IntegrationLogger(
            repository=integration_log_repo,
            origin_system=INTEGRATION_NAME,
            log_uuid=log_uuid,
        )

        parser = FidelizeObserverParser(
            db=db,
            origin_system=INTEGRATION_NAME,
            integration_id=van_context.integration_id,
        )

        pubsub_client = get_pubsub()
        publisher = ObserverPubSubPublisher(
            pubsub=pubsub_client,
            topic_map=OBSERVER_TOPICS,
        )

        # ── Pipeline ───────────────────────────────────────────────────
        pipeline = ObserverPipeline(
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
        )

        await pipeline.run()

    except Exception as e:
        logger.exception("❌ Fatal error in %s Observer: %s", INTEGRATION_NAME, e)
        raise
    finally:
        db.close()
        logger.info("DB session closed.")


if __name__ == "__main__":
    asyncio.run(run())

