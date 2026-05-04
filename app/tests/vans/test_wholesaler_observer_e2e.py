"""
Teste E2E: Observer Subscriber — fluxo completo com DB real + mock Fidelize server.

Valida o ciclo completo do Observer contra o banco PostgreSQL:
    Parser (DB real) → PubSub message → Subscriber → Auth (mock) → GraphQL mutation (mock)
    → _mark_as_delivered (DB real) → verifica flags no pre_pedido

Testa os 3 pedidos reais do banco (5001, 5002, 5003) nos fluxos:
    1. ORDER_RETURN           → createResponse → vans_confirmed = True
    2. ORDER_RETURN_REJECTION → createResponse → vans_confirmed = True
    3. RETURN_INVOICES        → createInvoice  → nf_confirmed = True
    4. RETURN_CANCELLATION    → createCancellation → order_cancellation_sent = True

DB real (PostgreSQL). VAN mockada via ASGITransport → mock Fidelize server.
Auth mockada (credenciais do mock server).
"""

import base64
import json
import pytest
from unittest.mock import MagicMock

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app as main_app
from app.infrastructure.db import SessionLocal
from app.infrastructure.db.models.vans.pre_pedidos import PrePedido
from app.tests.mocks.vans.mock_fidelize_server import (
    app as mock_fidelize_app,
    MOCK_USERNAME,
    MOCK_PASSWORD,
    reset_orders,
)
from app.api.v1.routes.api_sub.observer import get_httpx_transport
from app.api.v1.schemas.vans.observer_message import ObserverAction
from app.domain.entities.integrations.integration import IntegrationEntity
from app.infrastructure.auth.context import AuthContext
from app.infrastructure.auth.graphql_auth import GraphQLAuthProvider
from app.infrastructure.vans.auth.setup_contex import VanAuthContext


MOCK_BASE_URL = "http://mock-fidelize/graphql"
ORIGIN_SYSTEM = "Fidelize Funcional Wholesaler"
INTEGRATION_ID = 1

# Order codes dos 3 pedidos mock no banco
ORDER_CODES = ["5001", "5002", "5003"]


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _mock_van_context() -> VanAuthContext:
    """Cria VanAuthContext com credenciais do mock server."""
    provider = GraphQLAuthProvider(
        url=MOCK_BASE_URL,
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        mutation_name="createToken",
        response_token_field="token",
    )
    auth_ctx = AuthContext(
        integration_name=ORIGIN_SYSTEM,
        base_url=MOCK_BASE_URL,
        timeout=30,
        type_api="GRAPHQL",
        provider=provider,
    )
    return VanAuthContext(
        integration_name=ORIGIN_SYSTEM,
        integration_id=INTEGRATION_ID,
        auth=auth_ctx,
        db=MagicMock(),
    )


def _build_pubsub_request(action: ObserverAction, payload: dict) -> dict:
    """Monta payload PubSub no formato push subscription."""
    message = {
        "integration": ORIGIN_SYSTEM,
        "integration_id": INTEGRATION_ID,
        "action": action.value,
        "setup": {
            "check_id": "order_code",
            "query_parameters": {
                "order_code": str(payload.get("order_code", "?")),
                "industry_code": payload.get("industry_code", ""),
            },
        },
        "payload": payload,
    }
    b64 = base64.b64encode(json.dumps(message).encode()).decode()
    return {
        "subscription": "test-observer-sub",
        "message": {
            "data": b64,
            "messageId": "test-msg-001",
            "attributes": {
                "pub_id": "test-pub-id",
                "topic_id": "test-topic",
            },
        },
    }


def _get_pre_pedido(db, order_code: str) -> PrePedido:
    """Busca pre_pedido pelo origem_sistema_id."""
    return db.scalars(
        select(PrePedido).where(PrePedido.origem_sistema_id == order_code)
    ).first()


# ══════════════════════════════════════════════════════════════════════════════
#  Payloads — montados com dados reais dos 3 pre_pedidos do banco
# ══════════════════════════════════════════════════════════════════════════════

def _order_return_payload(order_code: int, industry_code: str = "SAN", pre_pedido_id: int | None = None) -> dict:
    return {
        "industry_code": industry_code,
        "order_code": order_code,
        "wholesaler_code": "98765432000199",
        "wholesaler_order_code": f"WH-{order_code}",
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
        ],
        "pre_pedido_id": pre_pedido_id,
        "pedido_datasul_id": order_code,
    }


def _invoice_payload(order_code: int, industry_code: str = "SAN", pre_pedido_id: int | None = None) -> dict:
    return {
        "industry_code": industry_code,
        "order_code": order_code,
        "wholesaler_code": "98765432000199",
        "customer_code": "12345678000100",
        "wholesaler_order_code": f"WH-{order_code}",
        "processed_at": "2026-03-30 12:00:00",
        "invoice_released_on": "2026-03-30",
        "invoice_code": f"NF-{order_code}",
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
        ],
        "pre_pedido_id": pre_pedido_id,
    }


def _cancellation_payload(order_code: int, industry_code: str = "SAN", pre_pedido_id: int | None = None) -> dict:
    return {
        "order_code": order_code,
        "industry_code": industry_code,
        "wholesaler_branch_code": "98765432000100",
        "products": [
            {"ean": "7899640800117"},
        ],
        "pre_pedido_id": pre_pedido_id,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_mock_server():
    """Reseta mock Fidelize server antes de cada teste."""
    reset_orders()
    yield


@pytest.fixture
def db():
    """Sessão do banco real (PostgreSQL)."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def reset_pre_pedido_flags(db):
    """
    Reseta flags dos 3 pre_pedidos antes e depois de cada teste.
    Garante que cada teste parte de um estado limpo.
    """
    for oc in ORDER_CODES:
        pp = _get_pre_pedido(db, oc)
        if pp:
            pp.vans_confirmed = False
            pp.nf_confirmed = None
            pp.order_cancellation_sent = None
    db.commit()

    yield

    # Cleanup: reseta de novo
    for oc in ORDER_CODES:
        pp = _get_pre_pedido(db, oc)
        if pp:
            pp.vans_confirmed = False
            pp.nf_confirmed = None
            pp.order_cancellation_sent = None
    db.commit()


MOCK_INTEGRATION = IntegrationEntity(
    id=INTEGRATION_ID,
    name=ORIGIN_SYSTEM,
    type_api="GRAPHQL",
    base_url=MOCK_BASE_URL,
    timeout=30,
    generic_fetcher=False,
)


@pytest.fixture(autouse=True)
def override_transport_and_auth(monkeypatch):
    """
    Mocks mínimos:
    - httpx_transport → ASGITransport para mock Fidelize server
    - SetupContext → auth com credenciais do mock server
    - IntegrationsRepository → base_url apontando pro mock (URL real é da Fidelize)

    Tudo mais (SessionLocal, RequestDetailsRepository, _mark_as_delivered) usa o banco real.
    """
    # Transport → mock Fidelize
    mock_transport = ASGITransport(app=mock_fidelize_app)
    main_app.dependency_overrides[get_httpx_transport] = lambda: mock_transport

    # SetupContext → credenciais do mock server
    def _setup_factory(db):
        setup = MagicMock()
        setup.load.return_value = _mock_van_context()
        return setup

    monkeypatch.setattr(
        "app.domain.services.vans.observer_subscriber_service.SetupContext",
        _setup_factory,
    )

    # IntegrationsRepository → base_url do mock (senão usa URL real da Fidelize)
    def _integrations_factory(db):
        repo = MagicMock()
        repo.get_by_id.return_value = MOCK_INTEGRATION
        return repo

    monkeypatch.setattr(
        "app.domain.services.vans.observer_subscriber_service.IntegrationsRepository",
        _integrations_factory,
    )

    yield

    main_app.dependency_overrides.pop(get_httpx_transport, None)


@pytest.fixture
def client():
    """AsyncClient apontando para a app FastAPI principal."""
    transport = ASGITransport(app=main_app)
    return AsyncClient(transport=transport, base_url="http://test")


# ══════════════════════════════════════════════════════════════════════════════
#  1. ORDER_RETURN — vans_confirmed = True
# ══════════════════════════════════════════════════════════════════════════════

class TestOrderReturn:
    """ORDER_RETURN → createResponse → marca vans_confirmed no banco."""

    @pytest.mark.asyncio
    async def test_order_return_5001_marks_vans_confirmed(self, client, db):
        """Envia ORDER_RETURN para 5001 e verifica vans_confirmed=True no banco."""
        pp = _get_pre_pedido(db, "5001")
        assert pp is not None, "PrePedido 5001 não encontrado no banco"
        assert pp.vans_confirmed is False

        payload = _order_return_payload(5001, "SAN", pre_pedido_id=pp.id)
        body = _build_pubsub_request(ObserverAction.ORDER_RETURN, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "ORDER_RETURN"
        assert data["order_code"] == "5001"
        assert data["van_status"] == 200

        # Verifica flag no banco
        db.expire_all()
        pp = _get_pre_pedido(db, "5001")
        assert pp.vans_confirmed is True

    @pytest.mark.asyncio
    async def test_order_return_5002_marks_vans_confirmed(self, client, db):
        """Envia ORDER_RETURN para 5002 e verifica vans_confirmed=True no banco."""
        pp = _get_pre_pedido(db, "5002")
        assert pp is not None
        assert pp.vans_confirmed is False

        payload = _order_return_payload(5002, "SAN", pre_pedido_id=pp.id)
        body = _build_pubsub_request(ObserverAction.ORDER_RETURN, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        db.expire_all()
        pp = _get_pre_pedido(db, "5002")
        assert pp.vans_confirmed is True

    @pytest.mark.asyncio
    async def test_order_return_5003_marks_vans_confirmed(self, client, db):
        """Envia ORDER_RETURN para 5003 e verifica vans_confirmed=True no banco."""
        pp = _get_pre_pedido(db, "5003")
        assert pp is not None
        assert pp.vans_confirmed is False

        payload = _order_return_payload(5003, "RCH", pre_pedido_id=pp.id)
        body = _build_pubsub_request(ObserverAction.ORDER_RETURN, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        db.expire_all()
        pp = _get_pre_pedido(db, "5003")
        assert pp.vans_confirmed is True

    @pytest.mark.asyncio
    async def test_all_three_orders_return(self, client, db):
        """Envia ORDER_RETURN para os 3 pedidos e verifica todos com vans_confirmed=True."""
        orders = [
            (5001, "SAN"),
            (5002, "SAN"),
            (5003, "RCH"),
        ]

        async with client:
            for order_code, industry in orders:
                pp = _get_pre_pedido(db, str(order_code))
                payload = _order_return_payload(order_code, industry, pre_pedido_id=pp.id)
                body = _build_pubsub_request(ObserverAction.ORDER_RETURN, payload)
                resp = await client.post("/observer-subscribe/observer", json=body)
                assert resp.json()["status"] == "ok", f"Falhou para order_code={order_code}: {resp.json()}"

        # Verifica todos no banco
        db.expire_all()
        for oc in ORDER_CODES:
            pp = _get_pre_pedido(db, oc)
            assert pp.vans_confirmed is True, f"PrePedido {oc}: vans_confirmed deveria ser True"


# ══════════════════════════════════════════════════════════════════════════════
#  2. ORDER_RETURN_REJECTION — vans_confirmed = True
# ══════════════════════════════════════════════════════════════════════════════

class TestOrderReturnRejection:
    """ORDER_RETURN_REJECTION → createResponse → marca vans_confirmed no banco."""

    @pytest.mark.asyncio
    async def test_order_rejection_marks_vans_confirmed(self, client, db):
        """Envia ORDER_RETURN_REJECTION para 5001 e verifica vans_confirmed=True."""
        pp = _get_pre_pedido(db, "5001")
        assert pp.vans_confirmed is False

        payload = _order_return_payload(5001, "SAN", pre_pedido_id=pp.id)
        payload["reason"] = "ORDER_REJECTED"
        body = _build_pubsub_request(ObserverAction.ORDER_RETURN_REJECTION, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["action"] == "ORDER_RETURN_REJECTION"

        db.expire_all()
        pp = _get_pre_pedido(db, "5001")
        assert pp.vans_confirmed is True


# ══════════════════════════════════════════════════════════════════════════════
#  3. RETURN_INVOICES — nf_confirmed = True
# ══════════════════════════════════════════════════════════════════════════════

class TestReturnInvoices:
    """RETURN_INVOICES → createInvoice → marca nf_confirmed no banco."""

    @pytest.mark.asyncio
    async def test_invoice_marks_nf_confirmed_by_pre_pedido_id(self, client, db):
        """Envia RETURN_INVOICES com pre_pedido_id e verifica nf_confirmed=True."""
        pp = _get_pre_pedido(db, "5001")
        assert pp.nf_confirmed is not True

        payload = _invoice_payload(5001, "SAN", pre_pedido_id=pp.id)
        body = _build_pubsub_request(ObserverAction.RETURN_INVOICES, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["action"] == "RETURN_INVOICES"

        db.expire_all()
        pp = _get_pre_pedido(db, "5001")
        assert pp.nf_confirmed is True

    @pytest.mark.asyncio
    async def test_invoice_marks_nf_confirmed_by_order_code(self, client, db):
        """Envia RETURN_INVOICES SEM pre_pedido_id — busca por order_code."""
        pp = _get_pre_pedido(db, "5002")
        assert pp.nf_confirmed is not True

        payload = _invoice_payload(5002, "SAN", pre_pedido_id=None)
        body = _build_pubsub_request(ObserverAction.RETURN_INVOICES, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        db.expire_all()
        pp = _get_pre_pedido(db, "5002")
        assert pp.nf_confirmed is True


# ══════════════════════════════════════════════════════════════════════════════
#  4. RETURN_CANCELLATION — order_cancellation_sent = True
# ══════════════════════════════════════════════════════════════════════════════

class TestReturnCancellation:
    """RETURN_CANCELLATION → createCancellation → marca order_cancellation_sent no banco."""

    @pytest.mark.asyncio
    async def test_cancellation_marks_order_cancellation_sent(self, client, db):
        """Envia RETURN_CANCELLATION para 5001 e verifica order_cancellation_sent=True."""
        pp = _get_pre_pedido(db, "5001")
        assert pp.order_cancellation_sent is not True

        payload = _cancellation_payload(5001, "SAN", pre_pedido_id=pp.id)
        body = _build_pubsub_request(ObserverAction.RETURN_CANCELLATION, payload)

        async with client:
            response = await client.post("/observer-subscribe/observer", json=body)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["action"] == "RETURN_CANCELLATION"

        db.expire_all()
        pp = _get_pre_pedido(db, "5001")
        assert pp.order_cancellation_sent is True


# ══════════════════════════════════════════════════════════════════════════════
#  5. Fluxo completo — os 4 actions sobre o mesmo pedido
# ══════════════════════════════════════════════════════════════════════════════

class TestFullObserverCycle:
    """Testa o ciclo completo do Observer sobre um único pedido."""

    @pytest.mark.asyncio
    async def test_full_cycle_on_5001(self, client, db):
        """
        Simula o ciclo de vida completo de um pedido:
            1. ORDER_RETURN → vans_confirmed = True
            2. RETURN_INVOICES → nf_confirmed = True
            3. RETURN_CANCELLATION → order_cancellation_sent = True

        Verifica cada flag individualmente no banco.
        """
        pp = _get_pre_pedido(db, "5001")
        pre_pedido_id = pp.id

        async with client:
            # ── 1. ORDER_RETURN ──
            body = _build_pubsub_request(
                ObserverAction.ORDER_RETURN,
                _order_return_payload(5001, "SAN", pre_pedido_id),
            )
            resp = await client.post("/observer-subscribe/observer", json=body)
            assert resp.json()["status"] == "ok"

            db.expire_all()
            pp = _get_pre_pedido(db, "5001")
            assert pp.vans_confirmed is True
            assert pp.nf_confirmed is not True
            assert pp.order_cancellation_sent is not True

            # ── 2. RETURN_INVOICES ──
            body = _build_pubsub_request(
                ObserverAction.RETURN_INVOICES,
                _invoice_payload(5001, "SAN", pre_pedido_id),
            )
            resp = await client.post("/observer-subscribe/observer", json=body)
            assert resp.json()["status"] == "ok"

            db.expire_all()
            pp = _get_pre_pedido(db, "5001")
            assert pp.vans_confirmed is True
            assert pp.nf_confirmed is True
            assert pp.order_cancellation_sent is not True

            # ── 3. RETURN_CANCELLATION ──
            body = _build_pubsub_request(
                ObserverAction.RETURN_CANCELLATION,
                _cancellation_payload(5001, "SAN", pre_pedido_id),
            )
            resp = await client.post("/observer-subscribe/observer", json=body)
            assert resp.json()["status"] == "ok"

            db.expire_all()
            pp = _get_pre_pedido(db, "5001")
            assert pp.vans_confirmed is True
            assert pp.nf_confirmed is True
            assert pp.order_cancellation_sent is True
