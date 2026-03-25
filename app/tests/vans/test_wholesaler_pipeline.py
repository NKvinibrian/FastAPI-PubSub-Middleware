"""
Testes do fluxo completo: Fidelize Funcional Wholesaler V2.

Testa todo o pipeline sem banco de dados e sem rede, usando
mocks in-memory para repositórios, GraphQL e PubSub.

Cobertura:
  1. OrderParser — converte raw orders → PrePedidoSchema
  2. OrderParser — salva LogPrePedidosVans por pedido
  3. PrePedidoPubSubPublisher — publica 1 mensagem por pedido
  4. PrePedidoPubSubPublisher — atualiza log com message_id
  5. FidelizeWholesalerFetcher — monta query correta (usa context=)
  6. FidelizeWholesalerFetcher — confirma pedidos (setOrderAsImported)
  7. IntegrationLogger — registra start/success/fail
  8. Pipeline completo via VanPipeline genérica — fetch → parse → publish → confirm
"""

import pytest
from copy import deepcopy
from uuid import uuid4

from app.api.v1.schemas.vans.pre_pedido import PrePedidoSchema, PrePedidoItemSchema
from app.domain.services.vans.order_parser import OrderParser
from app.domain.services.vans.integration_logger import IntegrationLogger
from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (
    FidelizeWholesalerFetcher,
)
from app.infrastructure.vans.pubsub.pre_pedido_publisher import PrePedidoPubSubPublisher
from app.pipelines.vans.van_pipeline import VanPipeline

from app.tests.mocks.vans.mocks import (
    MockLogPrePedidosVansRepository,
    MockIntegrationLogRepository,
    MockGraphQLFetcher,
    MockPubSub,
    SAMPLE_RAW_ORDERS,
)


ORIGIN_SYSTEM = "Fidelize Funcional Wholesaler"
INTEGRATION_ID = 1
PUBSUB_TOPIC = "merco-prepedido-datasul-test"


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def log_uuid():
    return uuid4()


@pytest.fixture
def log_prepedidos_repo():
    return MockLogPrePedidosVansRepository()


@pytest.fixture
def integration_log_repo():
    return MockIntegrationLogRepository()


@pytest.fixture
def mock_pubsub():
    return MockPubSub()


@pytest.fixture
def parser(log_prepedidos_repo, log_uuid):
    return OrderParser(
        log_repository=log_prepedidos_repo,
        origin_system=ORIGIN_SYSTEM,
        log_uuid=log_uuid,
        integration_id=INTEGRATION_ID,
    )


@pytest.fixture
def integration_logger(integration_log_repo, log_uuid):
    return IntegrationLogger(
        repository=integration_log_repo,
        origin_system=ORIGIN_SYSTEM,
        log_uuid=log_uuid,
    )


@pytest.fixture
def publisher(mock_pubsub, log_prepedidos_repo):
    return PrePedidoPubSubPublisher(
        pubsub=mock_pubsub,
        topic=PUBSUB_TOPIC,
        log_repository=log_prepedidos_repo,
    )


@pytest.fixture
def raw_orders():
    return deepcopy(SAMPLE_RAW_ORDERS)


# ═══════════════════════════════════════════════════════════════════════
#  1. OrderParser — parse
# ═══════════════════════════════════════════════════════════════════════

class TestOrderParser:

    def test_parse_returns_list_of_pre_pedido_schema(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, PrePedidoSchema) for r in result)

    def test_parse_maps_order_code_correctly(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].order_code == "5001"
        assert result[1].order_code == "5002"

    def test_parse_maps_origin_system(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].origin_system == ORIGIN_SYSTEM
        assert result[1].origin_system == ORIGIN_SYSTEM

    def test_parse_maps_origin_system_id(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].origin_system_id == "98001"
        assert result[1].origin_system_id == "98002"

    def test_parse_maps_industry_code(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].industry_code == "SAN"

    def test_parse_maps_customer_fields(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].customer_code == "12345678000100"
        assert result[0].customer_email == "cliente@test.com"
        assert result[0].customer_code_type == "CNPJ"

    def test_parse_maps_wholesaler_fields(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].wholesaler_code == "98765432000199"
        assert result[0].wholesaler_branch_code == "98765432000100"

    def test_parse_maps_products(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        products = result[0].products
        assert len(products) == 2
        assert all(isinstance(p, PrePedidoItemSchema) for p in products)

    def test_parse_maps_product_ean(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].products[0].ean == "7899640800117"
        assert result[0].products[1].ean == "7891058003203"

    def test_parse_maps_product_amount(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].products[0].amount == 3
        assert result[0].products[1].amount == 5

    def test_parse_maps_product_values(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        p = result[0].products[0]
        assert p.gross_value == 32.98
        assert p.discount_percentage == 10.0
        assert p.net_value == 29.69

    def test_parse_maps_product_monitored(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].products[0].monitored is False
        assert result[0].products[1].monitored is True

    def test_parse_handles_optional_fields_as_none(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[1].customer_email is None
        assert result[1].commercial_condition_code is None

    def test_parse_handles_scheduled_delivery(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].scheduled_delivery_order is False
        assert result[1].scheduled_delivery_order is True

    def test_parse_datetime_iso_format(self, parser, raw_orders):
        result = parser.parse(raw_orders)
        assert result[0].tradetools_created_at is not None
        assert result[0].tradetools_created_at.year == 2026

    def test_parse_empty_list_returns_empty(self, parser):
        result = parser.parse([])
        assert result == []

    def test_parse_single_order(self, parser, raw_orders):
        result = parser.parse([raw_orders[0]])
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════
#  2. OrderParser — LogPrePedidosVans
# ═══════════════════════════════════════════════════════════════════════

class TestOrderParserLogs:

    def test_parse_creates_log_per_order(self, parser, raw_orders, log_prepedidos_repo):
        parser.parse(raw_orders)
        assert len(log_prepedidos_repo.get_all()) == 2

    def test_log_has_correct_pedido_van_id(self, parser, raw_orders, log_prepedidos_repo):
        parser.parse(raw_orders)
        logs = log_prepedidos_repo.get_all()
        assert logs[0].pedido_van_id == "5001"
        assert logs[1].pedido_van_id == "5002"

    def test_log_has_correct_integration_id(self, parser, raw_orders, log_prepedidos_repo):
        parser.parse(raw_orders)
        logs = log_prepedidos_repo.get_all()
        assert all(l.integration_id == INTEGRATION_ID for l in logs)

    def test_log_status_is_parsed(self, parser, raw_orders, log_prepedidos_repo):
        parser.parse(raw_orders)
        logs = log_prepedidos_repo.get_all()
        assert all(l.integration_status == "PARSED" for l in logs)

    def test_log_has_log_uuid(self, parser, raw_orders, log_prepedidos_repo, log_uuid):
        parser.parse(raw_orders)
        logs = log_prepedidos_repo.get_all()
        assert all(l.log_uuid == log_uuid for l in logs)

    def test_log_message_id_is_none_initially(self, parser, raw_orders, log_prepedidos_repo):
        parser.parse(raw_orders)
        logs = log_prepedidos_repo.get_all()
        assert all(l.message_id is None for l in logs)

    def test_log_has_auto_incremented_id(self, parser, raw_orders, log_prepedidos_repo):
        parser.parse(raw_orders)
        logs = log_prepedidos_repo.get_all()
        assert logs[0].id == 1
        assert logs[1].id == 2


# ═══════════════════════════════════════════════════════════════════════
#  3. PrePedidoPubSubPublisher — publish
# ═══════════════════════════════════════════════════════════════════════

class TestPubSubPublisher:

    @pytest.mark.asyncio
    async def test_publish_sends_one_message_per_order(self, parser, publisher, raw_orders, log_uuid, mock_pubsub):
        parsed = parser.parse(raw_orders)
        await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert len(mock_pubsub.messages) == 2

    @pytest.mark.asyncio
    async def test_publish_returns_message_ids(self, parser, publisher, raw_orders, log_uuid):
        parsed = parser.parse(raw_orders)
        ids = await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert len(ids) == 2
        assert ids[0] == "1000"
        assert ids[1] == "1001"

    @pytest.mark.asyncio
    async def test_publish_uses_correct_topic(self, parser, publisher, raw_orders, log_uuid, mock_pubsub):
        parsed = parser.parse(raw_orders)
        await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert all(m["topic"] == PUBSUB_TOPIC for m in mock_pubsub.messages)

    @pytest.mark.asyncio
    async def test_publish_attributes_contain_order_code(self, parser, publisher, raw_orders, log_uuid, mock_pubsub):
        parsed = parser.parse(raw_orders)
        await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert mock_pubsub.messages[0]["attributes"]["order_code"] == "5001"
        assert mock_pubsub.messages[1]["attributes"]["order_code"] == "5002"

    @pytest.mark.asyncio
    async def test_publish_attributes_contain_origin_system(self, parser, publisher, raw_orders, log_uuid, mock_pubsub):
        parsed = parser.parse(raw_orders)
        await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert all(m["attributes"]["origin_system"] == ORIGIN_SYSTEM for m in mock_pubsub.messages)

    @pytest.mark.asyncio
    async def test_publish_message_is_valid_json(self, parser, publisher, raw_orders, log_uuid, mock_pubsub):
        import json
        parsed = parser.parse(raw_orders)
        await publisher.publish(orders=parsed, log_uuid=log_uuid)
        for msg in mock_pubsub.messages:
            data = json.loads(msg["message"])
            assert "order_code" in data
            assert "products" in data

    @pytest.mark.asyncio
    async def test_publish_updates_log_with_message_id(self, parser, publisher, raw_orders, log_uuid, log_prepedidos_repo):
        parsed = parser.parse(raw_orders)
        await publisher.publish(orders=parsed, log_uuid=log_uuid)
        logs = log_prepedidos_repo.get_all()
        published_logs = [l for l in logs if l.integration_status == "PUBLISHED"]
        assert len(published_logs) == 2

    @pytest.mark.asyncio
    async def test_publish_empty_list(self, publisher, log_uuid, mock_pubsub):
        ids = await publisher.publish(orders=[], log_uuid=log_uuid)
        assert ids == []
        assert len(mock_pubsub.messages) == 0


# ═══════════════════════════════════════════════════════════════════════
#  4. FidelizeWholesalerFetcher
# ═══════════════════════════════════════════════════════════════════════

class TestFidelizeWholesalerFetcher:

    @pytest.mark.asyncio
    async def test_get_pre_orders_returns_list(self):
        mock_fetcher = MockGraphQLFetcher(responses=[SAMPLE_RAW_ORDERS])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        result = await fetcher.get_pre_orders(context="SAN")
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_pre_orders_passes_extract_path(self):
        mock_fetcher = MockGraphQLFetcher(responses=[[]])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        await fetcher.get_pre_orders(context="SAN")
        call = mock_fetcher.calls[0]
        assert call["extract_path"] == ["orders", "data"]

    @pytest.mark.asyncio
    async def test_get_pre_orders_query_contains_industry_code(self):
        mock_fetcher = MockGraphQLFetcher(responses=[[]])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        await fetcher.get_pre_orders(context="FAB")
        query = mock_fetcher.calls[0]["query"]
        assert '"FAB"' in query

    @pytest.mark.asyncio
    async def test_get_pre_orders_query_contains_key_fields(self):
        mock_fetcher = MockGraphQLFetcher(responses=[[]])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        await fetcher.get_pre_orders(context="SAN")
        query = mock_fetcher.calls[0]["query"]
        assert "order_code" in query
        assert "customer_code" in query
        assert "products" in query
        assert "ean" in query

    @pytest.mark.asyncio
    async def test_get_pre_orders_empty_response_returns_empty_list(self):
        mock_fetcher = MockGraphQLFetcher(responses=[None])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        result = await fetcher.get_pre_orders(context="SAN")
        assert result == []

    @pytest.mark.asyncio
    async def test_set_orders_as_imported_calls_for_each_order(self):
        mock_fetcher = MockGraphQLFetcher(
            responses=[{"id": 1}, {"id": 2}, {"id": 3}]
        )
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        await fetcher.set_orders_as_imported(
            order_codes=["5001", "5002", "5003"],
            context="SAN",
        )
        assert len(mock_fetcher.calls) == 3

    @pytest.mark.asyncio
    async def test_set_orders_as_imported_mutation_contains_order_code(self):
        mock_fetcher = MockGraphQLFetcher(responses=[{"id": 1}])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        await fetcher.set_orders_as_imported(
            order_codes=["5001"],
            context="SAN",
        )
        query = mock_fetcher.calls[0]["query"]
        assert "setOrderAsImported" in query
        assert "5001" in query

    @pytest.mark.asyncio
    async def test_set_orders_as_imported_empty_list(self):
        mock_fetcher = MockGraphQLFetcher()
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        await fetcher.set_orders_as_imported(order_codes=[], context="SAN")
        assert len(mock_fetcher.calls) == 0

    @pytest.mark.asyncio
    async def test_set_orders_as_imported_raises_on_error(self):
        mock_fetcher = MockGraphQLFetcher(
            responses=[RuntimeError("GraphQL error")]
        )
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_fetcher)
        with pytest.raises(RuntimeError, match="GraphQL error"):
            await fetcher.set_orders_as_imported(
                order_codes=["5001"],
                context="SAN",
            )


# ═══════════════════════════════════════════════════════════════════════
#  5. IntegrationLogger
# ═══════════════════════════════════════════════════════════════════════

class TestIntegrationLogger:

    def test_start_creates_log_with_started_status(self, integration_logger, integration_log_repo):
        log = integration_logger.start(
            component_name="fetcher",
            process_name="TestProcess",
        )
        assert log.status == "STARTED"
        assert log.id is not None
        assert len(integration_log_repo.get_all()) == 1

    def test_start_sets_component_and_process(self, integration_logger):
        log = integration_logger.start(
            component_name="parser",
            process_name="OrderParser.parse",
            message_text="Parsing orders",
        )
        assert log.component_name == "parser"
        assert log.process_name == "OrderParser.parse"
        assert log.message_text == "Parsing orders"

    def test_success_updates_status(self, integration_logger):
        log = integration_logger.start(component_name="fetcher", process_name="Test")
        updated = integration_logger.success(log, message_text="Done")
        assert updated.status == "SUCCESS"
        assert updated.finished_at is not None
        assert updated.duration_ms is not None

    def test_fail_updates_status_and_error(self, integration_logger):
        log = integration_logger.start(component_name="fetcher", process_name="Test")
        updated = integration_logger.fail(log, error_details="Connection timeout")
        assert updated.status == "FAILED"
        assert updated.error_details == "Connection timeout"
        assert updated.finished_at is not None

    def test_success_sets_response_json(self, integration_logger):
        log = integration_logger.start(component_name="fetcher", process_name="Test")
        updated = integration_logger.success(log, response_json={"count": 5})
        assert updated.response_json == {"count": 5}

    def test_start_sets_log_uuid(self, integration_logger, log_uuid):
        log = integration_logger.start(component_name="test", process_name="Test")
        assert log.log_uuid == log_uuid

    def test_start_sets_origin_system(self, integration_logger):
        log = integration_logger.start(component_name="test", process_name="Test")
        assert log.origin_system == ORIGIN_SYSTEM


# ═══════════════════════════════════════════════════════════════════════
#  6. Pipeline completo — fetch → parse → publish (confirm no sub)
# ═══════════════════════════════════════════════════════════════════════

class TestFullPipeline:

    @pytest.mark.asyncio
    async def test_full_flow_fetch_parse_publish(
        self,
        parser,
        publisher,
        integration_logger,
        log_prepedidos_repo,
        integration_log_repo,
        mock_pubsub,
        log_uuid,
    ):
        """
        Simula o pipeline completo: fetch → parse → publish.
        O confirm acontece no subscriber do Datasul, não aqui.
        """
        mock_graphql_fetcher = MockGraphQLFetcher(
            responses=[
                deepcopy(SAMPLE_RAW_ORDERS),  # get_pre_orders
            ]
        )
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_graphql_fetcher)

        # ── FETCH ──
        fetch_log = integration_logger.start(
            component_name="fetcher",
            process_name="FidelizeWholesalerFetcher.get_pre_orders",
        )
        raw_orders = await fetcher.get_pre_orders(context="SAN")
        assert len(raw_orders) == 2
        integration_logger.success(fetch_log, message_text=f"Fetched {len(raw_orders)} orders")

        # ── PARSE ──
        parse_log = integration_logger.start(
            component_name="parser",
            process_name="OrderParser.parse",
        )
        parsed_orders = parser.parse(raw_orders)
        assert len(parsed_orders) == 2
        assert parsed_orders[0].order_code == "5001"
        assert parsed_orders[1].order_code == "5002"
        integration_logger.success(parse_log, message_text=f"Parsed {len(parsed_orders)} orders")

        # ── PUBLISH ──
        publish_log = integration_logger.start(
            component_name="pubsub",
            process_name="PrePedidoPubSubPublisher.publish",
        )
        message_ids = await publisher.publish(orders=parsed_orders, log_uuid=log_uuid)
        assert len(message_ids) == 2
        integration_logger.success(publish_log, message_text=f"Published {len(message_ids)} messages")

        # ══ ASSERTIONS ══

        # LogPrePedidosVans: 2 logs criados (um por pedido)
        pedido_logs = log_prepedidos_repo.get_all()
        assert len(pedido_logs) == 2
        assert all(l.integration_status == "PUBLISHED" for l in pedido_logs)
        assert all(l.message_id is not None for l in pedido_logs)

        # IntegrationLog: 3 etapas (fetch, parse, publish) — confirm no sub
        integration_logs = integration_log_repo.get_all()
        assert len(integration_logs) == 3
        success_logs = [l for l in integration_logs if l.status == "SUCCESS"]
        assert len(success_logs) == 3
        components = [l.component_name for l in success_logs]
        assert "fetcher" in components
        assert "parser" in components
        assert "pubsub" in components

        # PubSub: 2 mensagens publicadas
        assert len(mock_pubsub.messages) == 2

        # Fetcher: 1 chamada (só get_pre_orders, confirm no sub)
        assert len(mock_graphql_fetcher.calls) == 1

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_orders(
        self,
        parser,
        publisher,
        integration_logger,
        log_prepedidos_repo,
        mock_pubsub,
        log_uuid,
    ):
        """Se o fetcher retorna lista vazia, o pipeline para sem erros."""
        mock_graphql_fetcher = MockGraphQLFetcher(responses=[[]])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_graphql_fetcher)

        raw_orders = await fetcher.get_pre_orders(context="SAN")
        assert raw_orders == []

        parsed = parser.parse(raw_orders)
        assert parsed == []

        ids = await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert ids == []

        assert len(log_prepedidos_repo.get_all()) == 0
        assert len(mock_pubsub.messages) == 0

    @pytest.mark.asyncio
    async def test_pipeline_fetch_error_logged_as_failed(
        self,
        integration_logger,
        integration_log_repo,
    ):
        """Se o fetcher falha, o integration_logger registra FAILED."""
        mock_graphql_fetcher = MockGraphQLFetcher(
            responses=[RuntimeError("Network error")]
        )
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_graphql_fetcher)

        fetch_log = integration_logger.start(
            component_name="fetcher",
            process_name="FidelizeWholesalerFetcher.get_pre_orders",
        )

        try:
            await fetcher.get_pre_orders(context="SAN")
        except Exception as e:
            integration_logger.fail(fetch_log, error_details=repr(e))

        logs = integration_log_repo.get_all()
        failed = [l for l in logs if l.status == "FAILED"]
        assert len(failed) == 1
        assert "RuntimeError" in failed[0].error_details


# ═══════════════════════════════════════════════════════════════════════
#  7. VanPipeline genérica
# ═══════════════════════════════════════════════════════════════════════

class TestVanPipeline:

    def _make_fetcher(self, responses):
        mock_gql = MockGraphQLFetcher(responses=responses)
        return FidelizeWholesalerFetcher(fetcher=mock_gql), mock_gql

    @pytest.mark.asyncio
    async def test_pipeline_runs_one_context(
        self,
        parser,
        publisher,
        integration_logger,
        log_prepedidos_repo,
        mock_pubsub,
        log_uuid,
    ):
        """VanPipeline com loop_fn=['SAN'] executa fetch → parse → publish."""
        fetcher, mock_gql = self._make_fetcher([
            deepcopy(SAMPLE_RAW_ORDERS),  # get_pre_orders SAN
        ])

        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: ["SAN"],
            log_uuid=log_uuid,
        )

        await pipeline.run()

        assert len(mock_pubsub.messages) == 2
        assert len(log_prepedidos_repo.get_all()) == 2
        assert all(l.integration_status == "PUBLISHED" for l in log_prepedidos_repo.get_all())

    @pytest.mark.asyncio
    async def test_pipeline_runs_multiple_contexts(
        self,
        parser,
        publisher,
        integration_logger,
        log_prepedidos_repo,
        mock_pubsub,
        log_uuid,
    ):
        """VanPipeline com loop_fn=['SAN','RCH'] executa para cada context."""
        # SAN: 2 pedidos, RCH: 1 pedido (apenas o primeiro SAMPLE + versão recortada)
        san_orders = deepcopy(SAMPLE_RAW_ORDERS)
        rch_orders = [deepcopy(SAMPLE_RAW_ORDERS[0])]
        rch_orders[0]["order_code"] = "6001"
        rch_orders[0]["id"] = "99001"

        fetcher, mock_gql = self._make_fetcher([
            san_orders,      # get_pre_orders SAN
            rch_orders,      # get_pre_orders RCH
        ])

        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: ["SAN", "RCH"],
            log_uuid=log_uuid,
        )

        await pipeline.run()

        # 2 (SAN) + 1 (RCH) = 3 mensagens publicadas
        assert len(mock_pubsub.messages) == 3
        assert len(log_prepedidos_repo.get_all()) == 3

    @pytest.mark.asyncio
    async def test_pipeline_skips_context_with_no_orders(
        self,
        parser,
        publisher,
        integration_logger,
        mock_pubsub,
        log_uuid,
    ):
        """VanPipeline com resposta vazia não publica nem confirma."""
        fetcher, mock_gql = self._make_fetcher([[]])  # retorna vazio

        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: ["SAN"],
            log_uuid=log_uuid,
        )

        await pipeline.run()

        assert len(mock_pubsub.messages) == 0
        # Apenas 1 chamada ao fetcher (sem confirm)
        assert len(mock_gql.calls) == 1

    @pytest.mark.asyncio
    async def test_pipeline_logs_all_stages(
        self,
        parser,
        publisher,
        integration_logger,
        integration_log_repo,
        log_uuid,
    ):
        """VanPipeline registra log para cada etapa do pipeline (fetch, parse, pubsub)."""
        fetcher, _ = self._make_fetcher([
            deepcopy(SAMPLE_RAW_ORDERS),
        ])

        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: ["SAN"],
            log_uuid=log_uuid,
        )

        await pipeline.run()

        logs = integration_log_repo.get_all()
        assert len(logs) == 3
        components = {l.component_name for l in logs}
        assert components == {"fetcher", "parser", "pubsub"}
        assert all(l.status == "SUCCESS" for l in logs)

    @pytest.mark.asyncio
    async def test_pipeline_logs_fetch_failure(
        self,
        parser,
        publisher,
        integration_logger,
        integration_log_repo,
        mock_pubsub,
        log_uuid,
    ):
        """VanPipeline registra FAILED quando o fetcher levanta exceção."""
        fetcher, _ = self._make_fetcher([RuntimeError("timeout")])

        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: ["SAN"],
            log_uuid=log_uuid,
        )

        await pipeline.run()  # Não deve propagar — pipeline captura internamente

        logs = integration_log_repo.get_all()
        failed = [l for l in logs if l.status == "FAILED"]
        assert len(failed) == 1
        assert failed[0].component_name == "fetcher"
        # Nenhuma mensagem publicada
        assert len(mock_pubsub.messages) == 0

    @pytest.mark.asyncio
    async def test_pipeline_without_loop_using_none_context(
        self,
        parser,
        publisher,
        integration_logger,
        log_prepedidos_repo,
        mock_pubsub,
        log_uuid,
    ):
        """VanPipeline com loop_fn=[None] funciona para VANs sem loop."""
        orders_no_industry = [deepcopy(SAMPLE_RAW_ORDERS[0])]
        fetcher, _ = self._make_fetcher([orders_no_industry])

        pipeline = VanPipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=publisher,
            integration_logger=integration_logger,
            loop_fn=lambda: [None],  # VAN sem loop
            log_uuid=log_uuid,
        )

        await pipeline.run()

        assert len(mock_pubsub.messages) == 1
        assert len(log_prepedidos_repo.get_all()) == 1



