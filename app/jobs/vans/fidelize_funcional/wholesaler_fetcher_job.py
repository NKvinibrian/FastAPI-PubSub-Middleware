"""
Job de orquestração: Fidelize Funcional Wholesaler — Fetcher.

Fluxo delegado à VanPipeline genérica:
    Fetch → Parse → Publish → Confirm

O que é específico deste job:
  - INTEGRATION_NAME, INDUSTRY_CODES e PUBSUB_TOPIC
  - Montagem dos componentes (fetcher, parser, publisher, logger)
  - loop_fn: lambda que retorna INDUSTRY_CODES

Cada etapa registra um IntegrationLog com status STARTED → SUCCESS/FAILED.
"""

import asyncio
import logging
from uuid import uuid4, UUID

from app.infrastructure.db import SessionLocal

# Setup / Auth
from app.infrastructure.vans.auth.setup_contex import SetupContext

# Pipeline genérica
from app.pipelines.vans.van_pipeline import VanPipeline

# Parser
from app.domain.services.vans.order_parser import OrderParser

# PubSub
from app.infrastructure.vans.pubsub.pre_pedido_publisher import PrePedidoPubSubPublisher
from app.core.dependencies import get_pubsub, get_wholesaler_fetcher, get_van_backup

# Operations loader (request_details)
from app.infrastructure.vans.operations_loader import load_operations
from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (
    OPERATION_GET_PRE_ORDERS,
    OPERATION_SET_ORDERS_AS_IMPORTED,
)

# Repositories
from app.infrastructure.repositories.logging.vans import LogPrePedidosVansRepository
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
INDUSTRY_CODES = ["SAN", "RCH"]  # TODO: carregar do banco via SetupEntity.industrial_code
PUBSUB_TOPIC = "merco-prepedido-datasul"  # TODO: parametrizar via config/env


async def run() -> None:
    """
    Monta os componentes e delega a execução à VanPipeline genérica.
    """
    db = SessionLocal()
    log_uuid: UUID = uuid4()

    logger.info("═" * 60)
    logger.info("JOB: %s", INTEGRATION_NAME)
    logger.info("log_uuid: %s", log_uuid)
    logger.info("═" * 60)

    try:
        # ── Setup ──────────────────────────────────────────────────────
        setup = SetupContext(db=db)
        van_context = setup.load(INTEGRATION_NAME)

        # ── Operações (endpoints/headers de request_details) ───────────
        operations = load_operations(
            db=db,
            integration_id=van_context.integration_id,
            base_url=van_context.auth.base_url,
            operation_names=[
                OPERATION_GET_PRE_ORDERS,
                OPERATION_SET_ORDERS_AS_IMPORTED,
            ],
        )

        # ── Componentes ────────────────────────────────────────────────
        fetcher = get_wholesaler_fetcher(
            auth_context=van_context.auth,
            operations=operations,
        )

        backup = get_van_backup(integration_name=INTEGRATION_NAME)

        log_prepedidos_repo = LogPrePedidosVansRepository(db=db)
        integration_log_repo = IntegrationLogRepository(db=db)

        integration_logger = IntegrationLogger(
            repository=integration_log_repo,
            origin_system=INTEGRATION_NAME,
            log_uuid=log_uuid,
        )

        parser = OrderParser(
            log_repository=log_prepedidos_repo,
            origin_system=INTEGRATION_NAME,
            log_uuid=log_uuid,
            integration_id=van_context.integration_id,
        )

        pubsub_client = get_pubsub()
        publisher = PrePedidoPubSubPublisher(
            pubsub=pubsub_client,
            topic=PUBSUB_TOPIC,
            log_repository=log_prepedidos_repo,
        )

        # ── Pipeline ───────────────────────────────────────────────────
        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: INDUSTRY_CODES,
            log_uuid=log_uuid,
            backup=backup,
            backup_prefix="FF",
        )

        await pipeline.run()

    except Exception as e:
        logger.exception("❌ Fatal error in %s: %s", INTEGRATION_NAME, e)
        raise
    finally:
        db.close()
        logger.info("DB session closed.")


if __name__ == "__main__":
    asyncio.run(run())
