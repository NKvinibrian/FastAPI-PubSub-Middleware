"""
Job de orquestração: Fidelize Funcional Wholesaler — Fetcher.

Fluxo:
1. Setup — carrega integração + auth do banco
2. Fetch — busca pedidos não importados por industry_code
3. Parse — converte para PrePedidoSchema + salva LogPrePedidosVans
4. Publish — publica cada pedido no PubSub (1 por mensagem)
5. Confirm — marca pedidos como importados na Fidelize

Cada etapa registra um IntegrationLog com status STARTED → SUCCESS/FAILED.
"""

import asyncio
import logging
from uuid import uuid4, UUID

from app.infrastructure.db import SessionLocal

# Setup / Auth
from app.infrastructure.vans.auth.setup_contex import SetupContext

# Connectors / Fetchers
from app.infrastructure.vans.connectors.graphql_connector import GraphQLConnector
from app.infrastructure.vans.fetcher.graphql_fetcher import GraphQLFetcher
from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (
    FidelizeWholesalerFetcher,
)

# Parser
from app.domain.services.vans.order_parser import OrderParser

# PubSub
from app.infrastructure.vans.pubsub.pre_pedido_publisher import PrePedidoPubSubPublisher
from app.core.dependencies import get_pubsub, get_wholesaler_fetcher

# Repositories
from app.infrastructure.repositories.logs.vans import LogPrePedidosVansRepository
from app.infrastructure.repositories.logs.integrations import IntegrationLogRepository

# Logger helper
from app.domain.services.vans.integration_logger import IntegrationLogger

# Exceptions
from app.infrastructure.vans.exceptions.api import EmptyResponse

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "Fidelize Funcional Wholesaler"
INDUSTRY_CODES = ["SAN", "RCH"]  # TODO: carregar do banco via SetupEntity.industrial_code
PUBSUB_TOPIC = "merco-prepedido-datasul"  # TODO: parametrizar via config/env


async def run() -> None:
    """
    Executa o pipeline completo de fetch → parse → publish → confirm
    para cada industry_code configurado.
    """
    db = SessionLocal()
    log_uuid: UUID = uuid4()

    try:
        # ── 1. Setup ──────────────────────────────────────────────
        setup = SetupContext(db=db)
        van_context = setup.load(INTEGRATION_NAME)

        # ── 2. Montar componentes ─────────────────────────────────
        fetcher = get_wholesaler_fetcher(auth_context=van_context.auth)

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

        # ── 3. Loop por industry_code ─────────────────────────────
        for industry_code in INDUSTRY_CODES:
            await _process_industry(
                industry_code=industry_code,
                fetcher=fetcher,
                parser=parser,
                publisher=publisher,
                integration_logger=integration_logger,
                log_uuid=log_uuid,
            )

    except Exception as e:
        logger.exception("Fatal error in Fidelize Wholesaler fetcher job: %s", e)
        raise
    finally:
        db.close()


async def _process_industry(
    industry_code: str,
    fetcher: FidelizeWholesalerFetcher,
    parser: OrderParser,
    publisher: PrePedidoPubSubPublisher,
    integration_logger: IntegrationLogger,
    log_uuid: UUID,
) -> None:
    """
    Processa uma industry_code: fetch → parse → publish → confirm.

    Args:
        industry_code: Código da indústria (ex: SAN, RCH).
        fetcher: Fetcher da Fidelize já configurado.
        parser: Parser genérico de pedidos.
        publisher: Publisher genérico de PubSub.
        integration_logger: Helper de logging de integração.
        log_uuid: UUID do grupo de processamento.
    """

    # ── FETCH ─────────────────────────────────────────────────
    fetch_log = integration_logger.start(
        component_name="fetcher",
        process_name="FidelizeWholesalerFetcher.get_pre_orders",
        message_text=f"Fetching orders for industry_code={industry_code}",
    )

    try:
        raw_orders = await fetcher.get_pre_orders(industry_code=industry_code)

        if not raw_orders:
            integration_logger.success(
                fetch_log,
                message_text=f"No orders found for industry_code={industry_code}",
            )
            logger.info("No orders for industry_code=%s", industry_code)
            return

        integration_logger.success(
            fetch_log,
            message_text=f"Fetched {len(raw_orders)} orders for industry_code={industry_code}",
        )

    except EmptyResponse:
        integration_logger.success(
            fetch_log,
            message_text=f"Empty response for industry_code={industry_code}",
        )
        logger.warning("Empty response for industry_code=%s", industry_code)
        return

    except Exception as e:
        integration_logger.fail(fetch_log, error_details=repr(e))
        logger.exception("Fetch failed for industry_code=%s", industry_code)
        return

    # ── PARSE ─────────────────────────────────────────────────
    parse_log = integration_logger.start(
        component_name="parser",
        process_name="OrderParser.parse",
        message_text=f"Parsing {len(raw_orders)} orders",
    )

    try:
        parsed_orders = parser.parse(raw_orders)

        integration_logger.success(
            parse_log,
            message_text=f"Parsed {len(parsed_orders)} orders",
        )

    except Exception as e:
        integration_logger.fail(parse_log, error_details=repr(e))
        logger.exception("Parse failed for industry_code=%s", industry_code)
        return

    # ── PUBLISH ───────────────────────────────────────────────
    publish_log = integration_logger.start(
        component_name="pubsub",
        process_name="PrePedidoPubSubPublisher.publish",
        message_text=f"Publishing {len(parsed_orders)} orders",
    )

    try:
        message_ids = await publisher.publish(
            orders=parsed_orders,
            log_uuid=log_uuid,
        )

        integration_logger.success(
            publish_log,
            message_text=f"Published {len(message_ids)} messages",
        )

    except Exception as e:
        integration_logger.fail(publish_log, error_details=repr(e))
        logger.exception("Publish failed for industry_code=%s", industry_code)
        return

    # ── CONFIRM ───────────────────────────────────────────────
    confirm_log = integration_logger.start(
        component_name="confirm",
        process_name="FidelizeWholesalerFetcher.set_orders_as_imported",
        message_text=f"Confirming {len(parsed_orders)} orders as imported",
    )

    try:
        order_codes = [order.order_code for order in parsed_orders]

        await fetcher.set_orders_as_imported(
            order_codes=order_codes,
            industry_code=industry_code,
        )

        integration_logger.success(
            confirm_log,
            message_text=f"Confirmed {len(order_codes)} orders as imported",
        )

    except Exception as e:
        integration_logger.fail(confirm_log, error_details=repr(e))
        logger.exception("Confirm failed for industry_code=%s", industry_code)


if __name__ == "__main__":
    asyncio.run(run())

