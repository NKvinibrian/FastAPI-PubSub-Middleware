"""
Subscriber do Datasul — recebe pré-pedidos via PubSub e envia ao Datasul.

Fluxo:
    1. Recebe a mensagem PubSub (push subscription)
    2. Decodifica o PrePedidoSchema do payload base64
    3. Envia o pedido ao Datasul via send_pre_pedido
    4. Se ACEITO → confirma o pedido como importado na VAN de origem
    5. Se REJEITADO → loga o erro, não confirma (pedido ficará pendente)

O `origin_system` nos attributes da mensagem identifica qual VAN
originou o pedido, permitindo obter o fetcher correto para o confirm.
"""

import base64
import json
import logging

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.v1.schemas.api_sub.receiver import PubSub
from app.api.v1.schemas.vans.pre_pedido import PrePedidoSchema
from app.core.dependencies import get_datasul_service, get_van_confirmer
from app.domain.protocol.datasul.datasul import DatasulProtocol
from app.domain.protocol.vans.van_fetcher import VanFetcherProtocol

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/datasul-subscribe",
    tags=["Datasul subscription"],
)


@router.post("/pre-pedido-datasul", status_code=http_status.HTTP_200_OK)
async def pre_pedido_sub(
    request: PubSub,
    datasul_service: DatasulProtocol = Depends(get_datasul_service),
):
    """
    Endpoint de push subscription para pré-pedidos enviados ao Datasul.

    Fluxo:
        1. Decodifica a mensagem base64 → PrePedidoSchema
        2. Envia ao Datasul (login + send_pre_pedido)
        3. Se aceito → confirma na VAN de origem (set_orders_as_imported)
    """
    # ── 1. Decodifica a mensagem ─────────────────────────────────────────
    try:
        raw_b64 = request.message.data
        # O mock_pubsub envia como repr(b'...'), tratamos os dois formatos
        if raw_b64.startswith("b'") or raw_b64.startswith('b"'):
            decoded_bytes = eval(raw_b64)  # noqa: S307 — usado apenas com mock local
        else:
            decoded_bytes = base64.b64decode(raw_b64)

        payload = json.loads(decoded_bytes)
        order = PrePedidoSchema(**payload)
    except Exception as exc:
        logger.error("[DATASUL-SUB] ❌ Falha ao decodificar mensagem: %s", exc)
        return {"status": "error", "detail": f"Decode failed: {exc}"}

    order_code = order.order_code
    origin_system = order.origin_system
    industry_code = order.industry_code

    logger.info(
        "[DATASUL-SUB] 📩 Mensagem recebida | order_code=%s | origin=%s | industry=%s",
        order_code,
        origin_system,
        industry_code,
    )

    # ── 2. Envia ao Datasul ──────────────────────────────────────────────
    try:
        token = datasul_service.login(username="", password="")
        accepted = datasul_service.send_pre_pedido(token=token, data=order.model_dump())
    except Exception as exc:
        logger.exception("[DATASUL-SUB] ❌ Erro ao enviar ao Datasul order_code=%s", order_code)
        return {"status": "error", "detail": f"Datasul send failed: {exc}"}

    if not accepted:
        logger.warning(
            "[DATASUL-SUB] ⚠ Pedido REJEITADO pelo Datasul | order_code=%s",
            order_code,
        )
        return {"status": "rejected", "order_code": order_code}

    logger.info("[DATASUL-SUB] ✔ Pedido ACEITO pelo Datasul | order_code=%s", order_code)

    # ── 3. Confirma na VAN de origem ─────────────────────────────────────
    try:
        confirmer: VanFetcherProtocol = get_van_confirmer(origin_system)
        await confirmer.set_orders_as_imported(
            order_codes=[order_code],
            context=industry_code,
        )
        logger.info(
            "[DATASUL-SUB] ✔ Confirm na VAN | order_code=%s | origin=%s | context=%s",
            order_code,
            origin_system,
            industry_code,
        )
    except Exception as exc:
        logger.exception(
            "[DATASUL-SUB] ❌ Falha no confirm da VAN | order_code=%s | origin=%s",
            order_code,
            origin_system,
        )
        return {
            "status": "accepted_but_confirm_failed",
            "order_code": order_code,
            "detail": str(exc),
        }

    return {
        "status": "ok",
        "order_code": order_code,
        "datasul_accepted": True,
        "van_confirmed": True,
    }

