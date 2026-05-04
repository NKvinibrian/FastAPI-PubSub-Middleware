"""
Testes do ciclo de backup do VanPipeline (Landing → Processed/Failed).

Cobre o mesmo padrão do GCS legado, agora orquestrado pelo
VanPipeline com `MockBackupStorage` injetado:

  * Sucesso (fetch + parse + publish)        → Landing → Processed
  * Falha no parse                            → Landing → Failed
  * Falha no publish                          → Landing → Failed
  * Resposta vazia do fetcher                 → nada é gravado
  * Falha no upload Landing                   → pipeline segue normal
  * Pipeline sem backup configurado           → comportamento legado
  * Múltiplos contextos                       → 1 arquivo por contexto
"""

import json
from copy import deepcopy
from uuid import uuid4

import pytest

from app.domain.services.vans.integration_logger import IntegrationLogger
from app.domain.services.vans.order_parser import OrderParser
from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (
    FidelizeWholesalerFetcher,
)
from app.infrastructure.vans.pubsub.pre_pedido_publisher import PrePedidoPubSubPublisher
from app.pipelines.vans.van_pipeline import VanPipeline
from app.tests.mocks.vans.mock_backup_storage import MockBackupStorage
from app.tests.mocks.vans.mocks import (
    MockGraphQLFetcher,
    MockIntegrationLogRepository,
    MockLogPrePedidosVansRepository,
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
def backup():
    return MockBackupStorage(bucket_name="datahub-merco", base_path=ORIGIN_SYSTEM)


def _make_pipeline(*, fetcher, parser, publisher, integration_logger, log_uuid,
                   loop_fn, backup=None, backup_prefix="FF"):
    return VanPipeline(
        fetcher=fetcher,
        parser=parser,
        publisher=publisher,
        integration_logger=integration_logger,
        loop_fn=loop_fn,
        log_uuid=log_uuid,
        backup=backup,
        backup_prefix=backup_prefix,
    )


# ═══════════════════════════════════════════════════════════════════════
#  1. Sucesso → Landing → Processed
# ═══════════════════════════════════════════════════════════════════════

class TestBackupOnSuccess:

    @pytest.mark.asyncio
    async def test_success_uploads_landing_then_moves_to_processed(
        self, parser, publisher, integration_logger, log_uuid, backup
    ):
        mock_gql = MockGraphQLFetcher(responses=[deepcopy(SAMPLE_RAW_ORDERS)])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"], backup=backup,
        )

        await pipeline.run()

        # No final, nada em Landing — o arquivo foi movido pra Processed
        assert backup.landing == {}
        assert len(backup.processed) == 1
        assert len(backup.failed) == 0

        # Eventos: 1 upload + 1 move-to-Processed (nessa ordem)
        actions = [(e.action, e.folder) for e in backup.events]
        assert actions == [("upload", "Landing"), ("move", "Processed")]

    @pytest.mark.asyncio
    async def test_success_payload_is_json_of_raw_orders(
        self, parser, publisher, integration_logger, log_uuid, backup
    ):
        raw = deepcopy(SAMPLE_RAW_ORDERS)
        mock_gql = MockGraphQLFetcher(responses=[raw])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"], backup=backup,
        )

        await pipeline.run()

        (filename, payload), = backup.processed.items()
        decoded = json.loads(payload.decode("utf-8"))
        assert isinstance(decoded, list)
        assert len(decoded) == 2
        assert decoded[0]["order_code"] == "5001"

    @pytest.mark.asyncio
    async def test_success_filename_uses_prefix_and_context(
        self, parser, publisher, integration_logger, log_uuid, backup
    ):
        mock_gql = MockGraphQLFetcher(responses=[deepcopy(SAMPLE_RAW_ORDERS)])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"], backup=backup, backup_prefix="FF",
        )

        await pipeline.run()

        (filename,) = backup.processed.keys()
        assert filename.startswith("FF_")
        assert filename.endswith("_SAN.json")


# ═══════════════════════════════════════════════════════════════════════
#  2. Falha → Landing → Failed
# ═══════════════════════════════════════════════════════════════════════

class TestBackupOnFailure:

    @pytest.mark.asyncio
    async def test_parse_failure_moves_file_to_failed(
        self, publisher, integration_logger, log_prepedidos_repo, log_uuid, backup,
    ):
        # Parser que sempre falha
        class FailingParser:
            def parse(self, raw_orders):
                raise RuntimeError("parser blew up")

        mock_gql = MockGraphQLFetcher(responses=[deepcopy(SAMPLE_RAW_ORDERS)])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher,
            parser=FailingParser(),
            publisher=publisher,
            integration_logger=integration_logger,
            log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"],
            backup=backup,
        )

        await pipeline.run()

        assert backup.landing == {}
        assert backup.processed == {}
        assert len(backup.failed) == 1

        actions = [(e.action, e.folder) for e in backup.events]
        assert actions == [("upload", "Landing"), ("move", "Failed")]

    @pytest.mark.asyncio
    async def test_publish_failure_moves_file_to_failed(
        self, parser, integration_logger, log_uuid, backup,
    ):
        # Publisher que sempre falha
        class FailingPublisher:
            async def publish(self, orders, log_uuid):
                raise RuntimeError("pubsub blew up")

        mock_gql = MockGraphQLFetcher(responses=[deepcopy(SAMPLE_RAW_ORDERS)])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher,
            parser=parser,
            publisher=FailingPublisher(),
            integration_logger=integration_logger,
            log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"],
            backup=backup,
        )

        await pipeline.run()

        assert backup.landing == {}
        assert backup.processed == {}
        assert len(backup.failed) == 1


# ═══════════════════════════════════════════════════════════════════════
#  3. Sem pedidos → nenhum upload
# ═══════════════════════════════════════════════════════════════════════

class TestBackupSkippedWhenNoOrders:

    @pytest.mark.asyncio
    async def test_empty_response_does_not_touch_backup(
        self, parser, publisher, integration_logger, log_uuid, backup,
    ):
        mock_gql = MockGraphQLFetcher(responses=[[]])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"], backup=backup,
        )

        await pipeline.run()

        assert backup.landing == {}
        assert backup.processed == {}
        assert backup.failed == {}
        assert backup.events == []


# ═══════════════════════════════════════════════════════════════════════
#  4. Falha no upload Landing → pipeline segue normal
# ═══════════════════════════════════════════════════════════════════════

class TestBackupResilience:

    @pytest.mark.asyncio
    async def test_landing_upload_failure_does_not_break_pipeline(
        self, parser, publisher, integration_logger, mock_pubsub,
        log_prepedidos_repo, log_uuid, backup,
    ):
        backup.should_fail_upload = True

        mock_gql = MockGraphQLFetcher(responses=[deepcopy(SAMPLE_RAW_ORDERS)])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"], backup=backup,
        )

        await pipeline.run()

        # Mensagens publicadas mesmo sem backup
        assert len(mock_pubsub.messages) == 2
        assert len(log_prepedidos_repo.get_all()) == 2

        # Como o upload falhou, não há nada em Landing/Processed/Failed
        assert backup.landing == {}
        assert backup.processed == {}
        assert backup.failed == {}


# ═══════════════════════════════════════════════════════════════════════
#  5. Pipeline sem backup → comportamento legado
# ═══════════════════════════════════════════════════════════════════════

class TestPipelineWithoutBackup:

    @pytest.mark.asyncio
    async def test_no_backup_runs_normally(
        self, parser, publisher, integration_logger, mock_pubsub, log_uuid,
    ):
        mock_gql = MockGraphQLFetcher(responses=[deepcopy(SAMPLE_RAW_ORDERS)])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN"], backup=None,
        )

        await pipeline.run()

        assert len(mock_pubsub.messages) == 2


# ═══════════════════════════════════════════════════════════════════════
#  6. Múltiplos contextos → 1 arquivo por context
# ═══════════════════════════════════════════════════════════════════════

class TestMultipleContexts:

    @pytest.mark.asyncio
    async def test_each_context_gets_own_processed_file(
        self, parser, publisher, integration_logger, log_uuid, backup,
    ):
        san_orders = deepcopy(SAMPLE_RAW_ORDERS)
        rch_orders = [deepcopy(SAMPLE_RAW_ORDERS[0])]
        rch_orders[0]["order_code"] = "6001"
        rch_orders[0]["id"] = "99001"

        mock_gql = MockGraphQLFetcher(responses=[san_orders, rch_orders])
        fetcher = FidelizeWholesalerFetcher(fetcher=mock_gql)

        pipeline = _make_pipeline(
            fetcher=fetcher, parser=parser, publisher=publisher,
            integration_logger=integration_logger, log_uuid=log_uuid,
            loop_fn=lambda: ["SAN", "RCH"], backup=backup, backup_prefix="FF",
        )

        await pipeline.run()

        assert len(backup.processed) == 2
        assert len(backup.failed) == 0
        names = sorted(backup.processed.keys())
        assert any(n.endswith("_SAN.json") for n in names)
        assert any(n.endswith("_RCH.json") for n in names)


# ═══════════════════════════════════════════════════════════════════════
#  7. MockBackupStorage — API básica
# ═══════════════════════════════════════════════════════════════════════

class TestMockBackupStorage:

    def test_upload_then_move_to_processed(self):
        b = MockBackupStorage()
        b.upload_landing("a.json", "{}")
        assert "a.json" in b.landing
        b.move_to_processed("a.json")
        assert "a.json" not in b.landing
        assert "a.json" in b.processed

    def test_upload_then_move_to_failed(self):
        b = MockBackupStorage()
        b.upload_landing("a.json", b"{}")
        b.move_to_failed("a.json")
        assert "a.json" in b.failed
        assert "a.json" not in b.landing

    def test_move_unknown_file_raises(self):
        b = MockBackupStorage()
        with pytest.raises(FileNotFoundError):
            b.move_to_processed("missing.json")

    def test_should_fail_upload_raises(self):
        b = MockBackupStorage(should_fail_upload=True)
        with pytest.raises(RuntimeError):
            b.upload_landing("a.json", "{}")

    def test_events_captured_in_order(self):
        b = MockBackupStorage()
        b.upload_landing("a.json", "{}")
        b.upload_landing("b.json", "{}")
        b.move_to_processed("a.json")
        b.move_to_failed("b.json")
        actions = [(e.action, e.filename, e.folder) for e in b.events]
        assert actions == [
            ("upload", "a.json", "Landing"),
            ("upload", "b.json", "Landing"),
            ("move", "a.json", "Processed"),
            ("move", "b.json", "Failed"),
        ]
