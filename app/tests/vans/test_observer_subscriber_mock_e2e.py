"""
Teste E2E: Observer Subscriber com MockObserverSubscriberService.

Valida o fluxo completo do Observer SEM HTTP real à VAN:
    PubSub message → Endpoint → MockObserverSubscriberService
    → _mark_as_delivered (DB real) → verifica flags no pre_pedido

Diferença do test_wholesaler_observer_e2e.py:
    - Lá: usa mock Fidelize server (ASGITransport) + monkeypatch de auth
    - Aqui: usa MockObserverSubscriberService (zero HTTP, zero auth)

Testa os 4 fluxos sobre os pedidos reais do banco (5001, 5002, 5003):
    1. ORDER_RETURN           → vans_confirmed = True
    2. ORDER_RETURN_REJECTION → vans_confirmed = True
    3. RETURN_INVOICES        → nf_confirmed = True
    4. RETURN_CANCELLATION    → order_cancellation_sent = True

DB real (PostgreSQL). VAN mockada via MockObserverSubscriberService.
"""

import base64
import json
import pytest

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app as main_app
from app.infrastructure.db import SessionLocal
from app.infrastructure.db.models.vans.pre_pedidos import PrePedido
from app.api.v1.schemas.vans.observer_message import ObserverAction


ORIGIN_SYSTEM = "Fidelize Funcional Wholesaler"
INTEGRATION_ID = 1
ORDER_CODES = ["5001", "5002", "5003"]


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

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
#  Payloads
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

@pytest.fixture
def db():
    """Sessão do banco real (PostgreSQL)."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def reset_pre_pedido_flags(db):
    """Reseta flags dos pre_pedidos antes e depois de cada teste."""
    for oc in ORDER_CODES:
        pp = _get_pre_pedido(db, oc)
        if pp:
            pp.vans_confirmed = False
            pp.nf_confirmed = None
            pp.order_cancellation_sent = None
    db.commit()

    yield

    for oc in ORDER_CODES:
        pp = _get_pre_pedido(db, oc)
        if pp:
            pp.vans_confirmed = False
            pp.nf_confirmed = None
            pp.order_cancellation_sent = None
    db.commit()


@pytest.fixture(autouse=True)
def use_mock_observer_service(monkeypatch):
    """
    Garante MOCK_OBSERVER_VAN=true para que o get_observer_subscriber_service
    no dependencies retorne MockObserverSubscriberService.

    Limpa o lru_cache do get_settings para que a flag seja relida.
    """
    monkeypatch.setenv("MOCK_OBSERVER_VAN", "true")

    from app.core.config import get_settings
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def client():
    """AsyncClient apontando para a app FastAPI principal."""
    transport = ASGITransport(app=main_app)
    return AsyncClient(transport=transport, base_url="http://test")


# ══════════════════════════════════════════════════════════════════════════════
#  1. ORDER_RETURN — vans_confirmed = True
# ══════════════════════════════════════════════════════════════════════════════

class TestMockOrderReturn:
    """ORDER_RETURN via mock → vans_confirmed no banco."""

    @pytest.mark.asyncio
    async def test_order_return_marks_vans_confirmed(self, client, db):
        """Envia ORDER_RETURN para 5001 e verifica vans_confirmed=True."""
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

        db.expire_all()
        pp = _get_pre_pedido(db, "5001")
        assert pp.vans_confirmed is True

    @pytest.mark.asyncio
    async def test_all_three_orders_return(self, client, db):
        """Envia ORDER_RETURN para os 3 pedidos e verifica flags."""
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
                assert resp.json()["status"] == "ok", f"Falhou para order_code={order_code}"

        db.expire_all()
        for oc in ORDER_CODES:
            pp = _get_pre_pedido(db, oc)
            assert pp.vans_confirmed is True, f"PrePedido {oc}: vans_confirmed deveria ser True"


# ══════════════════════════════════════════════════════════════════════════════
#  2. ORDER_RETURN_REJECTION — vans_confirmed = True
# ══════════════════════════════════════════════════════════════════════════════

class TestMockOrderReturnRejection:
    """ORDER_RETURN_REJECTION via mock → vans_confirmed no banco."""

    @pytest.mark.asyncio
    async def test_order_rejection_marks_vans_confirmed(self, client, db):
        """Envia ORDER_RETURN_REJECTION e verifica vans_confirmed=True."""
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

class TestMockReturnInvoices:
    """RETURN_INVOICES via mock → nf_confirmed no banco."""

    @pytest.mark.asyncio
    async def test_invoice_marks_nf_confirmed_by_pre_pedido_id(self, client, db):
        """Envia RETURN_INVOICES com pre_pedido_id → nf_confirmed=True."""
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

class TestMockReturnCancellation:
    """RETURN_CANCELLATION via mock → order_cancellation_sent no banco."""

    @pytest.mark.asyncio
    async def test_cancellation_marks_order_cancellation_sent(self, client, db):
        """Envia RETURN_CANCELLATION e verifica order_cancellation_sent=True."""
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
#  5. Ciclo completo — os 4 actions sobre o mesmo pedido
# ══════════════════════════════════════════════════════════════════════════════

class TestMockFullObserverCycle:
    """Ciclo completo do Observer via mock sobre um único pedido."""

    @pytest.mark.asyncio
    async def test_full_cycle_on_5001(self, client, db):
        """
        Ciclo de vida completo:
            1. ORDER_RETURN → vans_confirmed = True
            2. RETURN_INVOICES → nf_confirmed = True
            3. RETURN_CANCELLATION → order_cancellation_sent = True
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
