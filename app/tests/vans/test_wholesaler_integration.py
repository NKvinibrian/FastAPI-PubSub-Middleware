"""
Teste de integração: Fidelize Wholesaler — fluxo completo com mock server.

Roda o pipeline REAL (auth → connector → fetcher → parser → pubsub → confirm)
contra um mock server ASGI que simula a API GraphQL da Fidelize.

Nenhuma chamada externa real. Tudo in-process via httpx.ASGITransport.
"""

import pytest
import httpx
from uuid import uuid4

from app.tests.mocks.vans.mock_fidelize_server import (
    app as mock_app,
    reset_orders,
    MOCK_USERNAME,
    MOCK_PASSWORD,
    MOCK_TOKEN,
)
from app.tests.mocks.vans.mocks import (
    MockLogPrePedidosVansRepository,
    MockIntegrationLogRepository,
    MockPubSub,
)

from app.infrastructure.auth.context import AuthContext
from app.infrastructure.auth.graphql_auth import GraphQLAuthProvider
from app.infrastructure.vans.connectors.graphql_connector import GraphQLConnector
from app.infrastructure.vans.fetcher.graphql_fetcher import GraphQLFetcher
from app.infrastructure.vans.integrations.fidelize_funcional.wholesaler_fetcher import (
    FidelizeWholesalerFetcher,
)
from app.domain.services.vans.order_parser import OrderParser
from app.domain.services.vans.integration_logger import IntegrationLogger
from app.infrastructure.vans.pubsub.pre_pedido_publisher import PrePedidoPubSubPublisher


MOCK_BASE_URL = "http://mock-fidelize/graphql"
ORIGIN_SYSTEM = "Fidelize Funcional Wholesaler"
INTEGRATION_ID = 1
PUBSUB_TOPIC = "merco-prepedido-datasul-test"


# ══════════════════════════════════════════════════════════════════════════════
#  Monkey-patch: fazer o GraphQLConnector e o AuthProvider usarem ASGITransport
# ══════════════════════════════════════════════════════════════════════════════

def _make_asgi_client() -> httpx.AsyncClient:
    """Cria um httpx.AsyncClient que roteia para o mock server ASGI."""
    transport = httpx.ASGITransport(app=mock_app)
    return httpx.AsyncClient(transport=transport, base_url=MOCK_BASE_URL)


class PatchedGraphQLConnector(GraphQLConnector):
    """
    GraphQLConnector que usa o mock server via ASGITransport
    em vez de fazer chamadas HTTP reais.
    """

    async def _resolve_token(self) -> str:
        """Resolve token usando ASGITransport para o mock server."""
        if self._token is not None:
            return self._token

        provider = self._auth_context.provider
        result = await provider.build_auth()

        if isinstance(result, httpx.Request):
            # Envia o request de auth via ASGITransport
            async with _make_asgi_client() as client:
                response = await client.send(result)
                response.raise_for_status()
                from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol
                if isinstance(provider, BaseAuthProviderProtocol):
                    self._token = provider.build_token_req(response)
                else:
                    self._token = response.text
        elif isinstance(result, dict):
            self._token = result.get("Authorization", "")

        return self._token or ""

    async def execute(self, query, variables=None, operation_name=None, extra_headers=None):
        """Executa query GraphQL via ASGITransport."""
        token = await self._resolve_token()

        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        if operation_name is not None:
            payload["operationName"] = operation_name

        async with _make_asgi_client() as client:
            response = await client.post(
                MOCK_BASE_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()

        if "errors" in body:
            raise RuntimeError(f"GraphQL errors: {body['errors']}")

        return body.get("data", {})


# ══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_mock_state():
    """Reseta o estado do mock server antes de cada teste."""
    reset_orders()
    yield


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
def auth_context():
    """AuthContext real usando GraphQLAuthProvider apontando pro mock."""
    provider = GraphQLAuthProvider(
        url=MOCK_BASE_URL,
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        mutation_name="createToken",
        response_token_field="token",
    )
    return AuthContext(
        integration_name=ORIGIN_SYSTEM,
        base_url=MOCK_BASE_URL,
        timeout=30,
        type_api="GRAPHQL",
        provider=provider,
    )


@pytest.fixture
def connector(auth_context):
    """GraphQLConnector patcheado para usar ASGITransport."""
    return PatchedGraphQLConnector(auth_context=auth_context)


@pytest.fixture
def fetcher(connector):
    graphql_fetcher = GraphQLFetcher(connector=connector)
    return FidelizeWholesalerFetcher(fetcher=graphql_fetcher)


@pytest.fixture
def parser(log_prepedidos_repo, log_uuid):
    return OrderParser(
        log_repository=log_prepedidos_repo,
        origin_system=ORIGIN_SYSTEM,
        log_uuid=log_uuid,
        integration_id=INTEGRATION_ID,
    )


@pytest.fixture
def publisher(mock_pubsub, log_prepedidos_repo):
    return PrePedidoPubSubPublisher(
        pubsub=mock_pubsub,
        topic=PUBSUB_TOPIC,
        log_repository=log_prepedidos_repo,
    )


@pytest.fixture
def integration_logger(integration_log_repo, log_uuid):
    return IntegrationLogger(
        repository=integration_log_repo,
        origin_system=ORIGIN_SYSTEM,
        log_uuid=log_uuid,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  1. Auth — login via createToken
# ══════════════════════════════════════════════════════════════════════════════

class TestMockAuth:

    @pytest.mark.asyncio
    async def test_connector_authenticates_with_mock_server(self, connector):
        """O connector consegue fazer login e cachear o token."""
        token = await connector._resolve_token()
        assert token == f"Bearer {MOCK_TOKEN}"

    @pytest.mark.asyncio
    async def test_connector_caches_token(self, connector):
        """Após primeira chamada, token é reutilizado."""
        t1 = await connector._resolve_token()
        t2 = await connector._resolve_token()
        assert t1 == t2

    @pytest.mark.asyncio
    async def test_auth_with_wrong_credentials_fails(self):
        """Credenciais erradas geram erro de autenticação."""
        provider = GraphQLAuthProvider(
            url=MOCK_BASE_URL,
            username="wrong",
            password="wrong",
        )
        ctx = AuthContext(
            integration_name=ORIGIN_SYSTEM,
            base_url=MOCK_BASE_URL,
            timeout=30,
            type_api="GRAPHQL",
            provider=provider,
        )
        conn = PatchedGraphQLConnector(auth_context=ctx)
        # O token extraído será None porque createToken retorna erro
        with pytest.raises(ValueError, match="Token not found"):
            await conn._resolve_token()


# ══════════════════════════════════════════════════════════════════════════════
#  2. Fetcher — get_pre_orders
# ══════════════════════════════════════════════════════════════════════════════

class TestMockFetcher:

    @pytest.mark.asyncio
    async def test_get_pre_orders_san(self, fetcher):
        """Busca pedidos com industry_code=SAN retorna os 2 pedidos SAN."""
        orders = await fetcher.get_pre_orders(industry_code="SAN")
        assert len(orders) == 2
        assert all(o["industry_code"] == "SAN" for o in orders)

    @pytest.mark.asyncio
    async def test_get_pre_orders_rch(self, fetcher):
        """Busca pedidos com industry_code=RCH retorna 1 pedido."""
        orders = await fetcher.get_pre_orders(industry_code="RCH")
        assert len(orders) == 1
        assert orders[0]["industry_code"] == "RCH"
        assert orders[0]["order_code"] == 5003

    @pytest.mark.asyncio
    async def test_get_pre_orders_unknown_industry_returns_empty(self, fetcher):
        """Industry code sem pedidos retorna lista vazia."""
        orders = await fetcher.get_pre_orders(industry_code="XXX")
        assert orders == []

    @pytest.mark.asyncio
    async def test_get_pre_orders_returns_products(self, fetcher):
        """Os pedidos retornados contêm produtos com todos os campos."""
        orders = await fetcher.get_pre_orders(industry_code="SAN")
        products = orders[0]["products"]
        assert len(products) == 2
        assert products[0]["ean"] == "7899640800117"
        assert products[0]["amount"] == 3
        assert products[0]["gross_value"] == 32.98


# ══════════════════════════════════════════════════════════════════════════════
#  3. Confirm — setOrderAsImported
# ══════════════════════════════════════════════════════════════════════════════

class TestMockConfirm:

    @pytest.mark.asyncio
    async def test_confirm_marks_orders_as_imported(self, fetcher):
        """Após confirmar, os pedidos não aparecem mais na query."""
        # Busca antes
        before = await fetcher.get_pre_orders(industry_code="SAN")
        assert len(before) == 2

        # Confirma
        codes = [o["order_code"] for o in before]
        await fetcher.set_orders_as_imported(order_codes=codes, industry_code="SAN")

        # Busca depois
        after = await fetcher.get_pre_orders(industry_code="SAN")
        assert len(after) == 0

    @pytest.mark.asyncio
    async def test_confirm_partial(self, fetcher):
        """Confirma só 1 pedido — o outro continua disponível."""
        await fetcher.set_orders_as_imported(order_codes=[5001], industry_code="SAN")

        remaining = await fetcher.get_pre_orders(industry_code="SAN")
        assert len(remaining) == 1
        assert remaining[0]["order_code"] == 5002

    @pytest.mark.asyncio
    async def test_confirm_does_not_affect_other_industry(self, fetcher):
        """Confirmar SAN não afeta pedidos RCH."""
        await fetcher.set_orders_as_imported(order_codes=[5001, 5002], industry_code="SAN")

        rch = await fetcher.get_pre_orders(industry_code="RCH")
        assert len(rch) == 1


# ══════════════════════════════════════════════════════════════════════════════
#  4. Parser — parse orders vindos do mock
# ══════════════════════════════════════════════════════════════════════════════

class TestMockParser:

    @pytest.mark.asyncio
    async def test_parse_orders_from_mock(self, fetcher, parser):
        """Pedidos vindos do mock são parseados corretamente."""
        raw = await fetcher.get_pre_orders(industry_code="SAN")
        parsed = parser.parse(raw)

        assert len(parsed) == 2
        assert parsed[0].order_code == "5001"
        assert parsed[0].origin_system == ORIGIN_SYSTEM
        assert parsed[0].industry_code == "SAN"
        assert len(parsed[0].products) == 2

    @pytest.mark.asyncio
    async def test_parse_creates_logs(self, fetcher, parser, log_prepedidos_repo):
        """Cada pedido parseado gera um LogPrePedidosVans."""
        raw = await fetcher.get_pre_orders(industry_code="SAN")
        parser.parse(raw)

        logs = log_prepedidos_repo.get_all()
        assert len(logs) == 2
        assert logs[0].pedido_van_id == "5001"
        assert logs[1].pedido_van_id == "5002"


# ══════════════════════════════════════════════════════════════════════════════
#  5. Pipeline completo — fetch → parse → publish → confirm
# ══════════════════════════════════════════════════════════════════════════════

class TestMockFullPipeline:

    @pytest.mark.asyncio
    async def test_full_pipeline_san(
        self,
        fetcher,
        parser,
        publisher,
        integration_logger,
        log_prepedidos_repo,
        integration_log_repo,
        mock_pubsub,
        log_uuid,
    ):
        """
        Fluxo completo para SAN:
        1. Fetch → 2 pedidos
        2. Parse → 2 PrePedidoSchema
        3. Publish → 2 mensagens no PubSub
        4. Confirm → pedidos desaparecem
        """
        # ── FETCH ──
        fetch_log = integration_logger.start(
            component_name="fetcher",
            process_name="FidelizeWholesalerFetcher.get_pre_orders",
        )
        raw_orders = await fetcher.get_pre_orders(industry_code="SAN")
        assert len(raw_orders) == 2
        integration_logger.success(fetch_log, message_text=f"Fetched {len(raw_orders)}")

        # ── PARSE ──
        parse_log = integration_logger.start(
            component_name="parser",
            process_name="OrderParser.parse",
        )
        parsed = parser.parse(raw_orders)
        assert len(parsed) == 2
        assert parsed[0].order_code == "5001"
        assert parsed[1].order_code == "5002"
        integration_logger.success(parse_log, message_text=f"Parsed {len(parsed)}")

        # ── PUBLISH ──
        pub_log = integration_logger.start(
            component_name="pubsub",
            process_name="PrePedidoPubSubPublisher.publish",
        )
        msg_ids = await publisher.publish(orders=parsed, log_uuid=log_uuid)
        assert len(msg_ids) == 2
        integration_logger.success(pub_log, message_text=f"Published {len(msg_ids)}")

        # ── CONFIRM ──
        confirm_log = integration_logger.start(
            component_name="confirm",
            process_name="FidelizeWholesalerFetcher.set_orders_as_imported",
        )
        order_codes = [o.order_code for o in parsed]
        await fetcher.set_orders_as_imported(order_codes=order_codes, industry_code="SAN")
        integration_logger.success(confirm_log, message_text="Confirmed")

        # ── ASSERTIONS ──

        # Pedidos sumiram da VAN
        remaining = await fetcher.get_pre_orders(industry_code="SAN")
        assert len(remaining) == 0

        # RCH não foi afetado
        rch = await fetcher.get_pre_orders(industry_code="RCH")
        assert len(rch) == 1

        # LogPrePedidosVans: 2 logs com status PUBLISHED
        pedido_logs = log_prepedidos_repo.get_all()
        assert len(pedido_logs) == 2
        assert all(l.integration_status == "PUBLISHED" for l in pedido_logs)
        assert all(l.message_id is not None for l in pedido_logs)

        # IntegrationLog: 4 etapas com status SUCCESS
        int_logs = integration_log_repo.get_all()
        assert len(int_logs) == 4
        assert all(l.status == "SUCCESS" for l in int_logs)
        components = {l.component_name for l in int_logs}
        assert components == {"fetcher", "parser", "pubsub", "confirm"}

        # PubSub: 2 mensagens
        assert len(mock_pubsub.messages) == 2
        assert mock_pubsub.messages[0]["attributes"]["order_code"] == "5001"
        assert mock_pubsub.messages[1]["attributes"]["order_code"] == "5002"

    @pytest.mark.asyncio
    async def test_full_pipeline_multi_industry(
        self, fetcher, parser, publisher, log_uuid, mock_pubsub, log_prepedidos_repo,
    ):
        """
        Roda o pipeline para SAN e RCH sequencialmente
        (como o job faz no loop de industry_codes).
        """
        total_parsed = []

        for industry in ["SAN", "RCH"]:
            raw = await fetcher.get_pre_orders(industry_code=industry)
            parsed = parser.parse(raw)
            await publisher.publish(orders=parsed, log_uuid=log_uuid)
            codes = [o.order_code for o in parsed]
            await fetcher.set_orders_as_imported(order_codes=codes, industry_code=industry)
            total_parsed.extend(parsed)

        # 3 pedidos no total (2 SAN + 1 RCH)
        assert len(total_parsed) == 3
        assert len(mock_pubsub.messages) == 3
        assert len(log_prepedidos_repo.get_all()) == 3

        # Todos confirmados — nada mais disponível
        assert await fetcher.get_pre_orders(industry_code="SAN") == []
        assert await fetcher.get_pre_orders(industry_code="RCH") == []

