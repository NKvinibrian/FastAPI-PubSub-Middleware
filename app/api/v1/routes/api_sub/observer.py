"""
Subscriber genérico do Observer — recebe mensagens PubSub e envia para a VAN.

Fluxo:
    1. Recebe mensagem PubSub (push subscription)
    2. Decodifica o ObserverMessageSchema do payload base64
    3. Usa integration_id + action para buscar RequestDetails no banco
       (template da requisição: endpoint, method, headers)
    4. Usa base_url + auth da integração para montar a request completa
    5. Envia para a VAN (GraphQL mutation ou REST)
    6. Se OK → retorna sucesso

O endpoint é genérico — funciona para QUALQUER VAN e QUALQUER action.
O subscriber não conhece os payloads específicos — ele apenas monta
a request usando os templates do banco (RequestDetails).
"""

import base64
import json
import logging

import httpx
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.v1.schemas.api_sub.receiver import PubSub
from app.api.v1.schemas.vans.observer_message import (
    ObserverAction,
    ObserverMessageSchema,
)
from app.infrastructure.db import SessionLocal
from app.infrastructure.repositories.integrations.integrations import IntegrationsRepository
from app.infrastructure.repositories.integrations.request_details import RequestDetailsRepository
from app.infrastructure.repositories.vans.pre_pedidos import PrePedidoRepository
from app.infrastructure.vans.auth.setup_contex import SetupContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/observer-subscribe",
    tags=["Observer subscription"],
)

# Mapeamento ObserverAction → nome no RequestDetails (campo name)
ACTION_TO_REQUEST_NAME: dict[ObserverAction, str] = {
    ObserverAction.ORDER_RETURN: "pedido_retorno",
    ObserverAction.ORDER_RETURN_REJECTION: "pedido_rejeicao",
    ObserverAction.RETURN_INVOICES: "nota_fiscal",
    ObserverAction.RETURN_CANCELLATION: "pedido_cancelamento",
}


def _decode_pubsub_data(raw_b64: str) -> dict:
    """Decodifica o campo data do PubSub (base64 → dict)."""
    return json.loads(base64.b64decode(raw_b64))


@router.post("/observer", status_code=http_status.HTTP_200_OK)
async def observer_sub(request: PubSub):
    """
    Endpoint genérico de push subscription para mensagens do Observer.

    Fluxo:
        1. Decodifica ObserverMessageSchema do payload base64
        2. Busca IntegrationEntity pelo integration_id → obtém base_url e auth
        3. Busca RequestDetails pelo integration_id + action (name)
        4. Monta a requisição (GraphQL mutation ou REST call)
        5. Envia para a VAN
        6. Se OK → {"status": "ok"}
    """
    # ── 1. Decodifica ────────────────────────────────────────────────────
    try:
        payload_dict = _decode_pubsub_data(request.message.data)
        message = ObserverMessageSchema(**payload_dict)
    except Exception as exc:
        logger.error("[OBSERVER-SUB] ❌ Falha ao decodificar mensagem: %s", exc)
        return {"status": "error", "detail": f"Decode failed: {exc}"}

    action = message.action
    integration_id = message.integration_id
    order_code = message.setup.query_parameters.get("order_code", "?")
    request_name = ACTION_TO_REQUEST_NAME.get(action)

    logger.info(
        "[OBSERVER-SUB] 📩 Recebido | action=%s | integration=%s (id=%d) | order_code=%s",
        action.value,
        message.integration,
        integration_id,
        order_code,
    )

    if not request_name:
        logger.error("[OBSERVER-SUB] ❌ Action desconhecida: %s", action.value)
        return {"status": "error", "detail": f"Unknown action: {action.value}"}

    # ── 2. Busca integração e request_details no banco ───────────────────
    db = SessionLocal()
    try:
        integrations_repo = IntegrationsRepository(db=db)
        integration = integrations_repo.get_by_id(integration_id)

        if not integration:
            logger.error("[OBSERVER-SUB] ❌ Integração não encontrada id=%d", integration_id)
            return {"status": "error", "detail": f"Integration not found: {integration_id}"}

        request_details_repo = RequestDetailsRepository(db=db)
        request_detail = request_details_repo.get_by_integration_and_name(
            integration_id=integration_id,
            name=request_name,
        )

        if not request_detail:
            logger.error(
                "[OBSERVER-SUB] ❌ RequestDetails não encontrado | integration_id=%d | name=%s",
                integration_id,
                request_name,
            )
            return {
                "status": "error",
                "detail": f"RequestDetails not found for integration_id={integration_id}, name={request_name}",
            }

        logger.info(
            "[OBSERVER-SUB] ✔ RequestDetails encontrado | endpoint=%s | method=%s",
            request_detail.endpoint,
            request_detail.request_method,
        )

        # ── 3. Monta auth (resolve token) ───────────────────────────────
        setup_ctx = SetupContext(db=db)
        van_context = setup_ctx.load(message.integration)
        auth_provider = van_context.auth.provider

        auth_result = await auth_provider.build_auth()
        if isinstance(auth_result, dict):
            auth_headers = auth_result
        else:
            # Se retorna httpx.Request, resolver o token
            async with httpx.AsyncClient() as client:
                auth_response = await client.send(auth_result)
                auth_response.raise_for_status()
                auth_headers = {"Authorization": auth_response.text}

        # ── 4. Monta a request e envia ──────────────────────────────────
        url = f"{integration.base_url.rstrip('/')}{request_detail.endpoint}"
        method = request_detail.request_method.upper()

        headers = {
            "Content-Type": "application/json",
            **(auth_headers or {}),
            **(request_detail.headers or {}),
        }

        request_type = (request_detail.request_type or "REST").upper()

        if request_type == "GRAPHQL":
            # Para GraphQL: o payload contém os dados, precisa montar a mutation
            # O endpoint do request_detail é o endpoint GraphQL da VAN
            # O payload já é o dict com os dados da mutation
            body = {
                "query": _build_graphql_mutation(action, message.payload),
            }
        else:
            # REST: envia o payload direto como JSON
            body = message.payload

        logger.info(
            "[OBSERVER-SUB] 📤 Enviando %s %s | order_code=%s",
            method,
            url,
            order_code,
        )

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=body,
                headers=headers,
                timeout=integration.timeout or 30,
            )

        if response.status_code >= 400:
            logger.error(
                "[OBSERVER-SUB] ❌ VAN respondeu %d | order_code=%s | body=%s",
                response.status_code,
                order_code,
                response.text[:500],
            )
            return {
                "status": "error",
                "order_code": order_code,
                "van_status": response.status_code,
                "detail": response.text[:500],
            }

        # Verifica erros GraphQL
        if request_type == "GRAPHQL":
            resp_json = response.json()
            if "errors" in resp_json:
                logger.error(
                    "[OBSERVER-SUB] ❌ GraphQL errors | order_code=%s | %s",
                    order_code,
                    resp_json["errors"],
                )
                return {
                    "status": "error",
                    "order_code": order_code,
                    "detail": str(resp_json["errors"]),
                }

        logger.info(
            "[OBSERVER-SUB] ✔ Enviado com sucesso | action=%s | order_code=%s | status=%d",
            action.value,
            order_code,
            response.status_code,
        )

        # ── 5. Marca o pré-pedido como entregue ──────────────────────────
        _mark_as_delivered(db, action, message.payload, order_code)

        return {
            "status": "ok",
            "action": action.value,
            "order_code": order_code,
            "van_status": response.status_code,
        }

    except Exception as exc:
        logger.exception("[OBSERVER-SUB] ❌ Erro inesperado | order_code=%s", order_code)
        return {"status": "error", "order_code": order_code, "detail": str(exc)}
    finally:
        db.close()


def _mark_as_delivered(
    db: Session,
    action: ObserverAction,
    payload: dict,
    order_code: str,
) -> None:
    """
    Após envio bem-sucedido à VAN, atualiza o pré-pedido no banco
    para indicar que a mensagem foi entregue.

    Flags atualizados por action:
        ORDER_RETURN / ORDER_RETURN_REJECTION → vans_confirmed = True
        RETURN_INVOICES → nf_confirmed = True
        RETURN_CANCELLATION → order_cancellation_sent = True
    """
    try:
        if action == ObserverAction.RETURN_INVOICES:
            pre_pedido_id = payload.get("pre_pedido_id")
            if pre_pedido_id:
                pp = db.scalars(
                    select(PrePedido).where(PrePedido.id == pre_pedido_id)
                ).first()
            else:
                pp = db.scalars(
                    select(PrePedido).where(
                        PrePedido.origem_sistema_id == str(order_code),
                    )
                ).first()

            if pp:
                pp.nf_confirmed = True
                db.commit()
                logger.info(
                    "[OBSERVER-SUB] ✔ Marcado nf_confirmed=True | pre_pedido.id=%d",
                    pp.id,
                )
            return

        pp = db.scalars(
            select(PrePedido).where(
                PrePedido.origem_sistema_id == str(order_code),
            )
        ).first()

        if not pp:
            logger.warning(
                "[OBSERVER-SUB] ⚠ PrePedido não encontrado para order_code=%s — skip confirm",
                order_code,
            )
            return

        if action in (ObserverAction.ORDER_RETURN, ObserverAction.ORDER_RETURN_REJECTION):
            pp.vans_confirmed = True
            db.commit()
            logger.info(
                "[OBSERVER-SUB] ✔ Marcado vans_confirmed=True | pre_pedido.id=%d",
                pp.id,
            )

        elif action == ObserverAction.RETURN_CANCELLATION:
            pp.order_cancellation_sent = True
            db.commit()
            logger.info(
                "[OBSERVER-SUB] ✔ Marcado order_cancellation_sent=True | pre_pedido.id=%d",
                pp.id,
            )

    except Exception as exc:
        logger.error(
            "[OBSERVER-SUB] ❌ Falha ao marcar entrega | action=%s | order_code=%s | %s",
            action.value,
            order_code,
            exc,
        )


def _build_graphql_mutation(action: ObserverAction, payload: dict) -> str:
    """
    Monta a mutation GraphQL a partir do action e payload.

    Cada action mapeia para uma mutation específica da VAN.
    O payload já contém os dados prontos — este método apenas
    formata como string GraphQL.
    """

    if action == ObserverAction.ORDER_RETURN or action == ObserverAction.ORDER_RETURN_REJECTION:
        return _build_create_response_mutation(payload)
    elif action == ObserverAction.RETURN_INVOICES:
        return _build_create_invoice_mutation(payload)
    elif action == ObserverAction.RETURN_CANCELLATION:
        return _build_create_cancellation_mutation(payload)
    else:
        raise ValueError(f"Unsupported action for GraphQL: {action.value}")


def _gql_str(v) -> str:
    """Formata valor para GraphQL: string entre aspas, null se None."""
    return "null" if v is None else f'"{v}"'


def _gql_num(v) -> str:
    """Formata valor numérico para GraphQL."""
    return "null" if v is None else str(v)


def _build_create_response_mutation(payload: dict) -> str:
    """Monta mutation createResponse a partir do payload."""
    products_parts = []
    for p in payload.get("products", []):
        products_parts.append(
            "{"
            f'ean: "{p.get("ean", "")}", '
            f'response_amount: {_gql_num(p.get("response_amount"))}, '
            f'unit_discount_percentage: {_gql_num(p.get("unit_discount_percentage"))}, '
            f'unit_discount_value: {_gql_num(p.get("unit_discount_value"))}, '
            f'unit_net_value: {_gql_num(p.get("unit_net_value"))}, '
            f'monitored: {str(p.get("monitored", False)).lower()}, '
            f'industry_consideration: {_gql_str(p.get("industry_consideration"))}'
            "}"
        )
    products_block = ", ".join(products_parts)

    args = [
        f'industry_code: "{payload.get("industry_code", "")}"',
        f'order_code: {int(payload.get("order_code"))}',
        f'wholesaler_code: "{payload.get("wholesaler_code", "")}"',
        f'processed_at: "{payload.get("processed_at", "")}"',
        f'reason: {payload.get("reason")}',
    ]
    if payload.get("wholesaler_order_code"):
        args.append(f'wholesaler_order_code: "{payload["wholesaler_order_code"]}"')
    if payload.get("payment_term"):
        args.append(f'payment_term: "{payload["payment_term"]}"')
    if payload.get("invoice_at"):
        args.append(f'invoice_at: "{payload["invoice_at"]}"')
    if payload.get("delivery_forecast_at"):
        args.append(f'delivery_forecast_at: "{payload["delivery_forecast_at"]}"')
    args.append(f"products: [ {products_block} ]")

    return (
        "mutation createResponse {\n"
        "  createResponse(\n    " + ",\n    ".join(args) + "\n  ) {\n"
        "    id\n    content\n    imported_at\n    outcome\n"
        "  }\n}"
    )


def _build_create_invoice_mutation(payload: dict) -> str:
    """Monta mutation createInvoice a partir do payload."""
    products_parts = []
    for p in payload.get("products", []):
        products_parts.append(
            "{"
            f'ean: "{p.get("ean", "")}", '
            f'invoice_amount: {_gql_num(p.get("invoice_amount"))}, '
            f'unit_discount_percentage: {_gql_num(p.get("unit_discount_percentage"))}, '
            f'unit_discount_value: {_gql_num(p.get("unit_discount_value"))}, '
            f'unit_net_value: {_gql_num(p.get("unit_net_value"))}'
            "}"
        )
    products_block = ", ".join(products_parts)

    args = [
        f'industry_code: "{payload.get("industry_code", "")}"',
        f'order_code: {int(payload.get("order_code"))}',
        f'wholesaler_code: "{payload.get("wholesaler_code", "")}"',
        f'customer_code: "{payload.get("customer_code", "")}"',
        f'processed_at: "{payload.get("processed_at", "")}"',
        f'invoice_released_on: "{payload.get("invoice_released_on", "")}"',
        f'invoice_code: "{payload.get("invoice_code", "")}"',
        f'invoice_value: {float(payload.get("invoice_value", 0))}',
        f'invoice_discount: {float(payload.get("invoice_discount", 0))}',
        f'invoice_danfe_key: "{payload.get("invoice_danfe_key", "")}"',
        f"products: [ {products_block} ]",
    ]
    if payload.get("wholesaler_order_code"):
        args.append(f'wholesaler_order_code: "{payload["wholesaler_order_code"]}"')

    return (
        "mutation createInvoice {\n"
        "  createInvoice(\n    " + ",\n    ".join(args) + "\n  ) {\n"
        "    id\n    content\n    imported_at\n    outcome\n"
        "  }\n}"
    )


def _build_create_cancellation_mutation(payload: dict) -> str:
    """Monta mutation createCancellation a partir do payload."""
    products_parts = [
        f'{{ ean: "{p.get("ean", "")}" }}'
        for p in payload.get("products", [])
    ]
    args = [
        f'order_code: {int(payload.get("order_code"))}',
        f'industry_code: "{payload.get("industry_code", "")}"',
        f'wholesaler_branch_code: "{payload.get("wholesaler_branch_code", "")}"',
        f"products: [ {', '.join(products_parts)} ]",
    ]

    return (
        "mutation createCancellation {\n"
        "  createCancellation(\n    " + ",\n    ".join(args) + "\n  ) {\n"
        "    id\n    content\n    imported_at\n    outcome\n"
        "  }\n}"
    )

