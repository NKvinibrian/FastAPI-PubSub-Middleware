"""
Teste E2E: Fidelize Wholesaler Observer — fluxo completo.

Valida o pipeline reverso do Observer:
    DB rows (mock) → Parser → Publisher → PubSub

Testa os 4 fluxos:
    1. ORDER_RETURN       — retorno de pedidos aceitos
    2. ORDER_RETURN_REJECTION — retorno de pedidos rejeitados
    3. RETURN_CANCELLATION — cancelamentos
    4. RETURN_INVOICES    — notas fiscais

Nenhuma chamada externa real. Tudo in-memory via mocks.
"""

import json
import pytest
from uuid import uuid4

from app.api.v1.schemas.vans.observer_message import ObserverAction
from app.domain.services.vans.integration_logger import IntegrationLogger
from app.infrastructure.vans.pubsub.observer_publisher import ObserverPubSubPublisher
from app.pipelines.vans.observer_pipeline import ObserverPipeline
from app.tests.mocks.vans.mocks import MockIntegrationLogRepository, MockPubSub
from app.tests.mocks.vans.mock_observer_parser import MockObserverParser


ORIGIN_SYSTEM = "Fidelize Funcional Wholesaler"
INTEGRATION_ID = 1

OBSERVER_TOPICS: dict[ObserverAction, str] = {
    ObserverAction.ORDER_RETURN: "merco-observer-order-return",
    ObserverAction.ORDER_RETURN_REJECTION: "merco-observer-order-rejection",
    ObserverAction.RETURN_INVOICES: "merco-observer-invoices",
    ObserverAction.RETURN_CANCELLATION: "merco-observer-cancellation",
}


# ══════════════════════════════════════════════════════════════════════════════
#  Dados brutos — simulam rows vindas do banco (pre_pedidos, NFs, etc.)
# ══════════════════════════════════════════════════════════════════════════════

DB_ORDER_RETURNS = [
    {
        "industry_code": "SAN",
        "order_code": 5001,
        "wholesaler_code": "12345678000100",
        "wholesaler_order_code": "WH-001",
        "payment_term": "30/60",
        "reason": "ORDER_SUCCESSFULLY_ACCEPTED",
        "processed_at": "2026-03-30 10:00:00",
        "invoice_at": None,
        "delivery_forecast_at": None,
        "products": [
            {
                "ean": "7899640800117",
                "response_amount": 3,
                "unit_discount_percentage": 0.0,
                "unit_discount_value": 0.0,
                "unit_net_value": 32.98,
                "monitored": False,
                "industry_consideration": "000",
            },
            {
                "ean": "7896015519100",
                "response_amount": 1,
                "unit_discount_percentage": 5.0,
                "unit_discount_value": 2.50,
                "unit_net_value": 47.50,
                "monitored": True,
                "industry_consideration": "000",
            },
        ],
    },
    {
        "industry_code": "SAN",
        "order_code": 5002,
        "wholesaler_code": "12345678000100",
        "wholesaler_order_code": "WH-002",
        "payment_term": "30",
        "reason": "ORDER_PARTIALLY_ACCEPTED",
        "processed_at": "2026-03-30 10:05:00",
        "invoice_at": None,
        "delivery_forecast_at": None,
        "products": [
            {
                "ean": "7891058003203",
                "response_amount": 5,
                "unit_discount_percentage": 0.0,
                "unit_discount_value": 0.0,
                "unit_net_value": 15.50,
                "monitored": False,
                "industry_consideration": "000",
            },
        ],
    },
]

DB_ORDER_REJECTIONS = [
    {
        "industry_code": "RCH",
        "order_code": 6001,
        "wholesaler_code": "98765432000199",
        "wholesaler_order_code": None,
        "payment_term": None,
        "reason": "ORDER_REJECTED",
        "processed_at": "2026-03-30 11:00:00",
        "invoice_at": None,
        "delivery_forecast_at": None,
        "products": [
            {
                "ean": "7896226503288",
                "response_amount": 10,
                "unit_discount_percentage": 0.0,
                "unit_discount_value": 0.0,
                "unit_net_value": 8.00,
                "monitored": False,
                "industry_consideration": "000",
            },
        ],
    },
]

DB_INVOICES = [
    {
        "industry_code": "SAN",
        "order_code": 5001,
        "wholesaler_code": "12345678000100",
        "customer_code": "11222333000144",
        "wholesaler_order_code": "WH-001",
        "processed_at": "2026-03-30 12:00:00",
        "invoice_released_on": "2026-03-30",
        "invoice_code": "NF-001234",
        "invoice_value": 146.44,
        "invoice_discount": 0.0,
        "invoice_danfe_key": "35260312345678000100550010001234561234567890",
        "products": [
            {
                "ean": "7899640800117",
                "invoice_amount": 3,
                "unit_discount_percentage": 0.0,
                "unit_discount_value": 0.0,
                "unit_net_value": 32.98,
            },
            {
                "ean": "7896015519100",
                "invoice_amount": 1,
                "unit_discount_percentage": 5.0,
                "unit_discount_value": 2.50,
                "unit_net_value": 47.50,
            },
        ],
    },
]

DB_CANCELLATIONS = [
    {
        "industry_code": "SAN",
        "order_code": 7001,
        "wholesaler_branch_code": "98765432000100",
        "products": [
            {"ean": "7899640800117"},
            {"ean": "7891058003203"},
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def log_uuid():
    return uuid4()


@pytest.fixture
def integration_log_repo():
    return MockIntegrationLogRepository()


@pytest.fixture
def mock_pubsub():
    return MockPubSub()


@pytest.fixture
def integration_logger(integration_log_repo, log_uuid):
    return IntegrationLogger(
        repository=integration_log_repo,
        origin_system=ORIGIN_SYSTEM,
        log_uuid=log_uuid,
    )


@pytest.fixture
def publisher(mock_pubsub):
    return ObserverPubSubPublisher(
        pubsub=mock_pubsub,
        topic_map=OBSERVER_TOPICS,
    )


@pytest.fixture
def full_parser():
    """Parser alimentado com dados dos 4 fluxos (simulando banco populado)."""
    return MockObserverParser(
        origin_system=ORIGIN_SYSTEM,
        integration_id=INTEGRATION_ID,
        order_returns_rows=DB_ORDER_RETURNS,
        order_rejections_rows=DB_ORDER_REJECTIONS,
        invoices_rows=DB_INVOICES,
        cancellations_rows=DB_CANCELLATIONS,
    )


@pytest.fixture
def empty_parser():
    """Parser sem dados no banco."""
    return MockObserverParser(
        origin_system=ORIGIN_SYSTEM,
        integration_id=INTEGRATION_ID,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  1. Parser — cada fluxo converte rows do banco em mensagens
# ══════════════════════════════════════════════════════════════════════════════

class TestObserverParser:

    def test_parse_order_returns(self, full_parser):
        """Rows de pedidos aceitos viram 2 mensagens ORDER_RETURN."""
        messages = full_parser.parse_order_returns()
        assert len(messages) == 2
        assert all(m.action == ObserverAction.ORDER_RETURN for m in messages)
        assert messages[0].setup.query_parameters["order_code"] == "5001"
        assert messages[1].setup.query_parameters["order_code"] == "5002"

    def test_parse_order_rejections(self, full_parser):
        """Row de pedido rejeitado vira 1 mensagem ORDER_RETURN_REJECTION."""
        messages = full_parser.parse_order_rejections()
        assert len(messages) == 1
        assert messages[0].action == ObserverAction.ORDER_RETURN_REJECTION
        assert messages[0].payload["reason"] == "ORDER_REJECTED"

    def test_parse_invoices(self, full_parser):
        """Row de NF vira 1 mensagem RETURN_INVOICES."""
        messages = full_parser.parse_invoices()
        assert len(messages) == 1
        assert messages[0].action == ObserverAction.RETURN_INVOICES
        assert messages[0].payload["invoice_code"] == "NF-001234"
        assert len(messages[0].payload["products"]) == 2

    def test_parse_cancellations(self, full_parser):
        """Row de cancelamento vira 1 mensagem RETURN_CANCELLATION."""
        messages = full_parser.parse_cancellations()
        assert len(messages) == 1
        assert messages[0].action == ObserverAction.RETURN_CANCELLATION
        assert messages[0].payload["order_code"] == 7001
        assert len(messages[0].payload["products"]) == 2

    def test_empty_parser_returns_empty(self, empty_parser):
        """Parser sem dados no banco retorna listas vazias."""
        assert empty_parser.parse_order_returns() == []
        assert empty_parser.parse_order_rejections() == []
        assert empty_parser.parse_invoices() == []
        assert empty_parser.parse_cancellations() == []


# ══════════════════════════════════════════════════════════════════════════════
#  2. Publisher — publica no tópico correto com atributos corretos
# ══════════════════════════════════════════════════════════════════════════════

class TestObserverPublisher:

    @pytest.mark.asyncio
    async def test_publish_order_returns(self, full_parser, publisher, mock_pubsub, log_uuid):
        """Publica ORDER_RETURN no tópico correto."""
        messages = full_parser.parse_order_returns()
        msg_ids = await publisher.publish(messages=messages, log_uuid=log_uuid)

        assert len(msg_ids) == 2
        assert len(mock_pubsub.messages) == 2

        for pub_msg in mock_pubsub.messages:
            assert pub_msg["topic"] == "merco-observer-order-return"
            assert pub_msg["attributes"]["action"] == "ORDER_RETURN"
            assert pub_msg["attributes"]["integration"] == ORIGIN_SYSTEM
            assert pub_msg["attributes"]["log_uuid"] == str(log_uuid)

        assert mock_pubsub.messages[0]["attributes"]["order_code"] == "5001"
        assert mock_pubsub.messages[1]["attributes"]["order_code"] == "5002"

    @pytest.mark.asyncio
    async def test_publish_order_rejections(self, full_parser, publisher, mock_pubsub, log_uuid):
        """Publica ORDER_RETURN_REJECTION no tópico correto."""
        messages = full_parser.parse_order_rejections()
        msg_ids = await publisher.publish(messages=messages, log_uuid=log_uuid)

        assert len(msg_ids) == 1
        assert mock_pubsub.messages[0]["topic"] == "merco-observer-order-rejection"
        assert mock_pubsub.messages[0]["attributes"]["action"] == "ORDER_RETURN_REJECTION"
        assert mock_pubsub.messages[0]["attributes"]["order_code"] == "6001"

    @pytest.mark.asyncio
    async def test_publish_invoices(self, full_parser, publisher, mock_pubsub, log_uuid):
        """Publica RETURN_INVOICES no tópico correto."""
        messages = full_parser.parse_invoices()
        msg_ids = await publisher.publish(messages=messages, log_uuid=log_uuid)

        assert len(msg_ids) == 1
        assert mock_pubsub.messages[0]["topic"] == "merco-observer-invoices"
        assert mock_pubsub.messages[0]["attributes"]["action"] == "RETURN_INVOICES"

    @pytest.mark.asyncio
    async def test_publish_cancellations(self, full_parser, publisher, mock_pubsub, log_uuid):
        """Publica RETURN_CANCELLATION no tópico correto."""
        messages = full_parser.parse_cancellations()
        msg_ids = await publisher.publish(messages=messages, log_uuid=log_uuid)

        assert len(msg_ids) == 1
        assert mock_pubsub.messages[0]["topic"] == "merco-observer-cancellation"
        assert mock_pubsub.messages[0]["attributes"]["action"] == "RETURN_CANCELLATION"

    @pytest.mark.asyncio
    async def test_publish_message_body_is_valid_json(self, full_parser, publisher, mock_pubsub, log_uuid):
        """O body publicado é JSON válido com os campos do ObserverMessageSchema."""
        messages = full_parser.parse_order_returns()
        await publisher.publish(messages=[messages[0]], log_uuid=log_uuid)

        body = json.loads(mock_pubsub.messages[0]["message"])
        assert body["integration"] == ORIGIN_SYSTEM
        assert body["action"] == "ORDER_RETURN"
        assert body["setup"]["check_id"] == "order_code"
        assert body["payload"]["order_code"] == 5001
        assert len(body["payload"]["products"]) == 2

    @pytest.mark.asyncio
    async def test_publish_empty_list(self, publisher, mock_pubsub, log_uuid):
        """Publicar lista vazia não gera mensagens."""
        msg_ids = await publisher.publish(messages=[], log_uuid=log_uuid)

        assert msg_ids == []
        assert len(mock_pubsub.messages) == 0


# ══════════════════════════════════════════════════════════════════════════════
#  3. Pipeline E2E — fluxo completo DB rows → Parse → Publish (4 fluxos)
# ══════════════════════════════════════════════════════════════════════════════

class TestObserverPipelineE2E:

    @pytest.mark.asyncio
    async def test_full_pipeline_all_flows(
        self,
        full_parser,
        publisher,
        integration_logger,
        integration_log_repo,
        mock_pubsub,
        log_uuid,
    ):
        """
        Pipeline completo com os 4 fluxos:
        - 2 ORDER_RETURN
        - 1 ORDER_RETURN_REJECTION
        - 1 RETURN_CANCELLATION
        - 1 RETURN_INVOICES
        Total: 5 mensagens publicadas.
        """
        pipeline = ObserverPipeline(
            parser=full_parser,
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
        )

        await pipeline.run()

        # ── 5 mensagens publicadas no total ──
        assert len(mock_pubsub.messages) == 5

        # ── Distribuição por tópico ──
        topics_published = [m["topic"] for m in mock_pubsub.messages]
        assert topics_published.count("merco-observer-order-return") == 2
        assert topics_published.count("merco-observer-order-rejection") == 1
        assert topics_published.count("merco-observer-cancellation") == 1
        assert topics_published.count("merco-observer-invoices") == 1

        # ── IntegrationLog: 4 fluxos × 2 etapas (parse + publish) = 8 logs ──
        int_logs = integration_log_repo.get_all()
        assert len(int_logs) == 8
        assert all(l.status == "SUCCESS" for l in int_logs)

    @pytest.mark.asyncio
    async def test_pipeline_empty_db(
        self,
        empty_parser,
        publisher,
        integration_logger,
        integration_log_repo,
        mock_pubsub,
        log_uuid,
    ):
        """
        Banco vazio: nenhum fluxo gera mensagens.
        Apenas 4 logs de parse com "Nenhum dado".
        """
        pipeline = ObserverPipeline(
            parser=empty_parser,
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
        )

        await pipeline.run()

        assert len(mock_pubsub.messages) == 0

        int_logs = integration_log_repo.get_all()
        assert len(int_logs) == 4
        assert all(l.status == "SUCCESS" for l in int_logs)
        assert all("Nenhum dado" in (l.message_text or "") for l in int_logs)

    @pytest.mark.asyncio
    async def test_pipeline_partial_flows(
        self,
        publisher,
        integration_logger,
        integration_log_repo,
        mock_pubsub,
        log_uuid,
    ):
        """
        Banco com apenas pedidos aceitos e NFs.
        Rejection e cancellation devem ser pulados.
        """
        partial_parser = MockObserverParser(
            origin_system=ORIGIN_SYSTEM,
            integration_id=INTEGRATION_ID,
            order_returns_rows=DB_ORDER_RETURNS,
            invoices_rows=DB_INVOICES,
        )

        pipeline = ObserverPipeline(
            parser=partial_parser,
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
        )

        await pipeline.run()

        # 2 ORDER_RETURN + 1 RETURN_INVOICES = 3 mensagens
        assert len(mock_pubsub.messages) == 3

        topics_published = [m["topic"] for m in mock_pubsub.messages]
        assert topics_published.count("merco-observer-order-return") == 2
        assert topics_published.count("merco-observer-invoices") == 1
        assert "merco-observer-order-rejection" not in topics_published
        assert "merco-observer-cancellation" not in topics_published

    @pytest.mark.asyncio
    async def test_pipeline_payloads_match_db_rows(
        self,
        full_parser,
        publisher,
        integration_logger,
        mock_pubsub,
        log_uuid,
    ):
        """
        Verifica que os payloads publicados correspondem
        aos dados originais do banco.
        """
        pipeline = ObserverPipeline(
            parser=full_parser,
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
        )

        await pipeline.run()

        # Agrupa mensagens publicadas por action
        by_action: dict[str, list[dict]] = {}
        for msg in mock_pubsub.messages:
            body = json.loads(msg["message"])
            action = body["action"]
            by_action.setdefault(action, []).append(body)

        # ORDER_RETURN: dados batem com DB_ORDER_RETURNS
        returns = by_action["ORDER_RETURN"]
        assert len(returns) == 2
        return_codes = {r["payload"]["order_code"] for r in returns}
        assert return_codes == {5001, 5002}

        ret_5001 = next(r for r in returns if r["payload"]["order_code"] == 5001)
        assert ret_5001["payload"]["reason"] == "ORDER_SUCCESSFULLY_ACCEPTED"
        assert len(ret_5001["payload"]["products"]) == 2

        # ORDER_RETURN_REJECTION: dados batem com DB_ORDER_REJECTIONS
        rejections = by_action["ORDER_RETURN_REJECTION"]
        assert rejections[0]["payload"]["order_code"] == 6001
        assert rejections[0]["payload"]["reason"] == "ORDER_REJECTED"

        # RETURN_INVOICES: dados batem com DB_INVOICES
        invoices = by_action["RETURN_INVOICES"]
        assert invoices[0]["payload"]["invoice_code"] == "NF-001234"
        assert invoices[0]["payload"]["invoice_danfe_key"] == "35260312345678000100550010001234561234567890"

        # RETURN_CANCELLATION: dados batem com DB_CANCELLATIONS
        cancellations = by_action["RETURN_CANCELLATION"]
        assert cancellations[0]["payload"]["order_code"] == 7001
        assert len(cancellations[0]["payload"]["products"]) == 2

    @pytest.mark.asyncio
    async def test_pipeline_execution_order(
        self,
        full_parser,
        publisher,
        integration_logger,
        mock_pubsub,
        log_uuid,
    ):
        """
        Verifica ordem de execução:
        ORDER_RETURN → ORDER_RETURN_REJECTION → RETURN_CANCELLATION → RETURN_INVOICES.
        """
        pipeline = ObserverPipeline(
            parser=full_parser,
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
        )

        await pipeline.run()

        actions_in_order = [m["attributes"]["action"] for m in mock_pubsub.messages]

        assert actions_in_order[0] == "ORDER_RETURN"
        assert actions_in_order[1] == "ORDER_RETURN"
        assert actions_in_order[2] == "ORDER_RETURN_REJECTION"
        assert actions_in_order[3] == "RETURN_CANCELLATION"
        assert actions_in_order[4] == "RETURN_INVOICES"