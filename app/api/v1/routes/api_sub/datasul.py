"""
Subscriber do Datasul — recebe pré-pedidos via PubSub, persiste no banco e envia ao Datasul.

Fluxo:
    1. Recebe a mensagem PubSub (push subscription)
    2. Decodifica o PrePedidoSchema do payload base64
    3. Persiste o pré-pedido e seus itens na tabela pre_pedidos/pre_pedido_itens
       (upsert — idempotente por origem_sistema_id)
    4. Marca erp_sended = True
    5. Envia o pedido ao Datasul via send_pre_pedido
    6. Se ACEITO  → erp_confirmed = True + confirma na VAN de origem
    7. Se REJEITADO → erp_returned = True

O `origin_system` nos attributes da mensagem identifica qual VAN
originou o pedido, permitindo obter o fetcher correto para o confirm.
"""

import base64
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.v1.schemas.api_sub.receiver import PubSub
from app.api.v1.schemas.vans.pre_pedido import PrePedidoSchema
from app.core.dependencies import get_datasul_service, get_van_confirmer
from app.domain.entities.vans.pre_pedidos import PrePedidoEntity, PrePedidoItemEntity
from app.domain.protocol.datasul.datasul import DatasulProtocol
from app.domain.protocol.vans.van_fetcher import VanFetcherProtocol
from app.infrastructure.db import SessionLocal
from app.infrastructure.repositories.vans.pre_pedidos import (
    PrePedidoItemRepository,
    PrePedidoRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/datasul-subscribe",
    tags=["Datasul subscription"],
)


def _schema_to_entity(order: PrePedidoSchema, pub_id: str) -> PrePedidoEntity:
    """Converte PrePedidoSchema em PrePedidoEntity pronto para persistência."""
    return PrePedidoEntity(
        origem_sistema_id=order.order_code,
        origem_industria_pedido_id=order.origin_system_id,
        origem_industria_codigo=order.industry_code,
        origem_sistema=order.origin_system,
        origem_log_uuid=UUID(pub_id) if pub_id else None,
        origem_industria_created_at=order.tradetools_created_at,
        informacoes_adicionais=order.additional_information,
        observacao=order.notification_obs,
        status=True,
        distribuidor_cnpj=order.wholesaler_code,
        distribuidor_filial_cnpj=order.wholesaler_branch_code,
        prazo_negociado=order.order_payment_term,
        condicao_comercial=order.commercial_condition_code,
        entrega_programada=order.scheduled_delivery_order,
        cliente_cpf_cnpj=order.customer_code,
        cliente_email=order.customer_email,
        erp_sended=True,
        erp_confirmed=False,
        erp_returned=False,
        vans_confirmed=False,
        nf_confirmed=False,
        order_cancellation_sent=False,
    )


def _save_pre_pedido(order: PrePedidoSchema, pub_id: str) -> int:
    """
    Persiste o pré-pedido e seus itens no banco.

    Upsert por origem_sistema_id:
        - Se já existe → apenas marca erp_sended = True e retorna o id
        - Se não existe → cria o registro com todos os campos

    Returns:
        int: ID do pre_pedido no banco.
    """
    db = SessionLocal()
    try:
        pre_pedido_repo = PrePedidoRepository(db=db)
        item_repo = PrePedidoItemRepository(db=db)

        existing = pre_pedido_repo.get_by_origem_sistema_id(order.order_code)

        if existing:
            logger.info(
                "[DATASUL-SUB] PrePedido já existe id=%d | order_code=%s — marcando erp_sended",
                existing.id,
                order.order_code,
            )
            existing.erp_sended = True
            pre_pedido_repo.update(existing)
            return existing.id

        entity = _schema_to_entity(order, pub_id)
        saved = pre_pedido_repo.create(entity)

        for product in order.products:
            item_repo.create(
                PrePedidoItemEntity(
                    pre_pedido_id=saved.id,
                    ean=product.ean,
                    quantidade=product.amount,
                    valor_bruto=product.gross_value,
                    desconto_percentual=product.discount_percentage,
                    valor_liquido=product.net_value,
                    produto_monitorado=product.monitored,
                    prazo=product.payment_term,
                )
            )

        logger.info(
            "[DATASUL-SUB] ✔ PrePedido salvo id=%d | order_code=%s | itens=%d",
            saved.id,
            order.order_code,
            len(order.products),
        )
        return saved.id

    except Exception:
        logger.exception(
            "[DATASUL-SUB] ❌ Falha ao salvar pre_pedido | order_code=%s", order.order_code
        )
        raise
    finally:
        db.close()


def _update_erp_status(pre_pedido_id: int, *, accepted: bool) -> None:
    """Atualiza erp_confirmed ou erp_returned após resposta do Datasul."""
    db = SessionLocal()
    try:
        repo = PrePedidoRepository(db=db)
        entity = repo.get_by_id(pre_pedido_id)
        if not entity:
            logger.warning("[DATASUL-SUB] ⚠ PrePedido id=%d não encontrado para update ERP", pre_pedido_id)
            return

        if accepted:
            entity.erp_confirmed = True
        else:
            entity.erp_returned = True

        repo.update(entity)
    except Exception:
        logger.exception("[DATASUL-SUB] ❌ Falha ao atualizar status ERP | pre_pedido_id=%d", pre_pedido_id)
    finally:
        db.close()


@router.post("/pre-pedido-datasul", status_code=http_status.HTTP_200_OK)
async def pre_pedido_sub(
    request: PubSub,
    datasul_service: DatasulProtocol = Depends(get_datasul_service),
):
    """
    Endpoint de push subscription para pré-pedidos enviados ao Datasul.

    Fluxo:
        1. Decodifica a mensagem base64 → PrePedidoSchema
        2. Persiste o pré-pedido e itens no banco (upsert idempotente)
        3. Envia ao Datasul
        4. Atualiza erp_confirmed / erp_returned conforme resposta
        5. Se aceito → confirma na VAN de origem
    """
    # ── 1. Decodifica ────────────────────────────────────────────────────
    try:
        decoded_bytes = base64.b64decode(request.message.data)
        payload = json.loads(decoded_bytes)
        order = PrePedidoSchema(**payload)
    except Exception as exc:
        logger.error("[DATASUL-SUB] ❌ Falha ao decodificar mensagem: %s", exc)
        return {"status": "error", "detail": f"Decode failed: {exc}"}

    order_code = order.order_code
    origin_system = order.origin_system
    industry_code = order.industry_code
    pub_id = request.message.attributes.pub_id

    logger.info(
        "[DATASUL-SUB] 📩 Mensagem recebida | order_code=%s | origin=%s | industry=%s",
        order_code,
        origin_system,
        industry_code,
    )

    # ── 2. Persiste no banco ─────────────────────────────────────────────
    try:
        pre_pedido_id = _save_pre_pedido(order, pub_id)
    except Exception as exc:
        return {"status": "error", "order_code": order_code, "detail": f"DB save failed: {exc}"}

    # ── 3. Envia ao Datasul ──────────────────────────────────────────────
    try:
        token = datasul_service.login(username="", password="")
        accepted = datasul_service.send_pre_pedido(token=token, data=order.model_dump())
    except Exception as exc:
        logger.exception("[DATASUL-SUB] ❌ Erro ao enviar ao Datasul order_code=%s", order_code)
        return {"status": "error", "order_code": order_code, "detail": f"Datasul send failed: {exc}"}

    # ── 4. Atualiza status ERP ───────────────────────────────────────────
    _update_erp_status(pre_pedido_id, accepted=accepted)

    if not accepted:
        logger.warning(
            "[DATASUL-SUB] ⚠ Pedido REJEITADO pelo Datasul | order_code=%s",
            order_code,
        )
        return {"status": "rejected", "order_code": order_code}

    logger.info("[DATASUL-SUB] ✔ Pedido ACEITO pelo Datasul | order_code=%s", order_code)

    # ── 5. Confirma na VAN de origem ─────────────────────────────────────
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
        "pre_pedido_id": pre_pedido_id,
        "datasul_accepted": True,
        "van_confirmed": True,
    }
