"""
Subscriber genérico do Observer — recebe mensagens PubSub e envia para a VAN.

Fluxo:
    1. Recebe mensagem PubSub (push subscription)
    2. Decodifica o ObserverMessageSchema do payload base64
    3. Delega para o ObserverSubscriberService (real ou mock) que:
       - Busca config da integração e request details
       - Resolve auth da VAN (ou simula envio no mock)
       - Monta e envia a request (GraphQL ou REST)
       - Marca pré-pedido como entregue
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.v1.schemas.api_sub.receiver import PubSub
from app.core.dependencies import get_observer_subscriber_service
from app.domain.services.vans.observer_subscriber_service import decode_pubsub_message
from app.infrastructure.db import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/observer-subscribe",
    tags=["Observer subscription"],
)


def get_httpx_transport() -> Optional[httpx.AsyncBaseTransport]:
    """
    Dependency que fornece o transport HTTP para chamadas à VAN.

    Em produção retorna None (transport padrão do httpx).
    Em testes, sobrescreva via app.dependency_overrides para injetar
    um ASGITransport apontando para o mock server.
    """
    return None


@router.post("/observer", status_code=http_status.HTTP_200_OK)
async def observer_sub(
    request: PubSub,
    httpx_transport: Optional[httpx.AsyncBaseTransport] = Depends(get_httpx_transport),
):
    """
    Endpoint genérico de push subscription para mensagens do Observer.

    Decodifica a mensagem PubSub e delega para o service (real ou mock
    conforme MOCK_OBSERVER_VAN no .env).
    """
    # ── 1. Decodifica ────────────────────────────────────────────────────
    try:
        message = decode_pubsub_message(request.message.data)
    except Exception as exc:
        logger.error("[OBSERVER-SUB] ❌ Falha ao decodificar mensagem: %s", exc)
        return {"status": "error", "detail": f"Decode failed: {exc}"}

    # ── 2. Processa via service ──────────────────────────────────────────
    db = SessionLocal()
    try:
        service = get_observer_subscriber_service(db=db, httpx_transport=httpx_transport)
        return await service.process(message)
    except Exception as exc:
        order_code = message.setup.query_parameters.get("order_code", "?")
        logger.exception("[OBSERVER-SUB] ❌ Erro inesperado | order_code=%s", order_code)
        return {"status": "error", "order_code": order_code, "detail": str(exc)}
    finally:
        db.close()
