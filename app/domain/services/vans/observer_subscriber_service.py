"""
Service do Observer Subscriber — orquestra o envio de mensagens para a VAN.

Fluxo:
    1. Decodifica ObserverMessageSchema do payload PubSub
    2. Busca IntegrationEntity e RequestDetails no banco
    3. Resolve autenticação da VAN
    4. Monta e envia a requisição (GraphQL ou REST)
    5. Marca o pré-pedido como entregue
"""

import base64
import json
import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.api.v1.schemas.vans.observer_message import (
    ObserverAction,
    ObserverMessageSchema,
)
from app.domain.services.vans.graphql_mutation_builder import build_graphql_mutation
from app.infrastructure.repositories.integrations.integrations import IntegrationsRepository
from app.infrastructure.repositories.integrations.request_details import RequestDetailsRepository
from app.infrastructure.repositories.vans.pre_pedidos import PrePedidoRepository
from app.infrastructure.vans.auth.setup_contex import SetupContext

logger = logging.getLogger(__name__)

ACTION_TO_REQUEST_NAME: dict[ObserverAction, str] = {
    ObserverAction.ORDER_RETURN: "pedido_retorno",
    ObserverAction.ORDER_RETURN_REJECTION: "pedido_rejeicao",
    ObserverAction.RETURN_INVOICES: "nota_fiscal",
    ObserverAction.RETURN_CANCELLATION: "pedido_cancelamento",
}

# Flags atualizados no PrePedido por action
_ACTION_FLAG_MAP: dict[ObserverAction, str] = {
    ObserverAction.ORDER_RETURN: "vans_confirmed",
    ObserverAction.ORDER_RETURN_REJECTION: "vans_confirmed",
    ObserverAction.RETURN_INVOICES: "nf_confirmed",
    ObserverAction.RETURN_CANCELLATION: "order_cancellation_sent",
}


def decode_pubsub_message(raw_b64: str) -> ObserverMessageSchema:
    """Decodifica o campo data do PubSub (base64 → ObserverMessageSchema)."""
    payload_dict = json.loads(base64.b64decode(raw_b64))
    return ObserverMessageSchema(**payload_dict)


class ObserverSubscriberService:
    """
    Orquestra o envio de mensagens do Observer para a VAN.

    Responsabilidades:
        - Buscar integração e request details no banco
        - Resolver auth da VAN
        - Montar e enviar a request (GraphQL ou REST)
        - Marcar pré-pedido como entregue
    """

    def __init__(
        self,
        db: Session,
        httpx_transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._db = db
        self._transport = httpx_transport
        self._integrations_repo = IntegrationsRepository(db=db)
        self._request_details_repo = RequestDetailsRepository(db=db)
        self._pre_pedido_repo = PrePedidoRepository(db=db)

    async def process(self, message: ObserverMessageSchema) -> dict:
        """
        Processa uma mensagem do Observer: busca config, autentica, envia, marca entrega.

        Returns:
            dict com status, action, order_code e van_status.
        """
        action = message.action
        integration_id = message.integration_id
        order_code = message.setup.query_parameters.get("order_code", "?")
        request_name = ACTION_TO_REQUEST_NAME.get(action)

        logger.info(
            "[OBSERVER-SUB] 📩 Recebido | action=%s | integration=%s (id=%d) | order_code=%s",
            action.value, message.integration, integration_id, order_code,
        )

        if not request_name:
            logger.error("[OBSERVER-SUB] ❌ Action desconhecida: %s", action.value)
            return {"status": "error", "detail": f"Unknown action: {action.value}"}

        # ── 1. Busca integração e request_details ───────────────────────
        integration = self._integrations_repo.get_by_id(integration_id)
        if not integration:
            logger.error("[OBSERVER-SUB] ❌ Integração não encontrada id=%d", integration_id)
            return {"status": "error", "detail": f"Integration not found: {integration_id}"}

        request_detail = self._request_details_repo.get_by_integration_and_name(
            integration_id=integration_id, name=request_name,
        )
        if not request_detail:
            logger.error(
                "[OBSERVER-SUB] ❌ RequestDetails não encontrado | integration_id=%d | name=%s",
                integration_id, request_name,
            )
            return {
                "status": "error",
                "detail": f"RequestDetails not found for integration_id={integration_id}, name={request_name}",
            }

        logger.info(
            "[OBSERVER-SUB] ✔ RequestDetails encontrado | endpoint=%s | method=%s",
            request_detail.endpoint, request_detail.request_method,
        )

        # ── 2. Resolve auth ─────────────────────────────────────────────
        auth_headers = await self._resolve_auth(message.integration)

        # ── 3. Monta e envia a request ──────────────────────────────────
        response = await self._send_request(
            integration=integration,
            request_detail=request_detail,
            action=action,
            payload=message.payload,
            auth_headers=auth_headers,
            order_code=order_code,
        )

        if response.status_code >= 400:
            logger.error(
                "[OBSERVER-SUB] ❌ VAN respondeu %d | order_code=%s | body=%s",
                response.status_code, order_code, response.text[:500],
            )
            return {
                "status": "error",
                "order_code": order_code,
                "van_status": response.status_code,
                "detail": response.text[:500],
            }

        request_type = (request_detail.request_type or "REST").upper()
        if request_type == "GRAPHQL":
            resp_json = response.json()
            if "errors" in resp_json:
                logger.error(
                    "[OBSERVER-SUB] ❌ GraphQL errors | order_code=%s | %s",
                    order_code, resp_json["errors"],
                )
                return {
                    "status": "error",
                    "order_code": order_code,
                    "detail": str(resp_json["errors"]),
                }

        logger.info(
            "[OBSERVER-SUB] ✔ Enviado com sucesso | action=%s | order_code=%s | status=%d",
            action.value, order_code, response.status_code,
        )

        # ── 4. Marca pré-pedido como entregue ───────────────────────────
        self._mark_as_delivered(action, message.payload, order_code)

        return {
            "status": "ok",
            "action": action.value,
            "order_code": order_code,
            "van_status": response.status_code,
        }

    async def _resolve_auth(self, integration_name: str) -> dict:
        """Resolve token/headers de auth da VAN."""
        setup_ctx = SetupContext(db=self._db)
        van_context = setup_ctx.load(integration_name)
        auth_provider = van_context.auth.provider

        auth_result = await auth_provider.build_auth()
        if isinstance(auth_result, dict):
            return auth_result

        async with httpx.AsyncClient(transport=self._transport) as client:
            auth_response = await client.send(auth_result)
            auth_response.raise_for_status()
            token = auth_provider.build_token_req(auth_response)
            return {"Authorization": token}

    async def _send_request(
        self,
        integration,
        request_detail,
        action: ObserverAction,
        payload: dict,
        auth_headers: dict,
        order_code: str,
    ) -> httpx.Response:
        """Monta e envia a requisição HTTP para a VAN."""
        url = f"{integration.base_url.rstrip('/')}{request_detail.endpoint}"
        method = request_detail.request_method.upper()
        request_type = (request_detail.request_type or "REST").upper()

        headers = {
            "Content-Type": "application/json",
            **(auth_headers or {}),
            **(request_detail.headers or {}),
        }

        if request_type == "GRAPHQL":
            body = {"query": build_graphql_mutation(action, payload)}
        else:
            body = payload

        logger.info("[OBSERVER-SUB] 📤 Enviando %s %s | order_code=%s", method, url, order_code)

        async with httpx.AsyncClient(transport=self._transport) as client:
            return await client.request(
                method=method,
                url=url,
                json=body,
                headers=headers,
                timeout=integration.timeout or 30,
            )

    def _mark_as_delivered(
        self,
        action: ObserverAction,
        payload: dict,
        order_code: str,
    ) -> None:
        """
        Atualiza o pré-pedido no banco para indicar que a mensagem foi entregue.

        Usa PrePedidoRepository em vez de queries diretas.
        """
        try:
            # Para RETURN_INVOICES, tenta buscar por pre_pedido_id primeiro
            if action == ObserverAction.RETURN_INVOICES:
                pre_pedido_id = payload.get("pre_pedido_id")
                if pre_pedido_id:
                    pp = self._pre_pedido_repo.get_by_id(pre_pedido_id)
                else:
                    pp = self._pre_pedido_repo.get_by_origem_sistema_id(str(order_code))
            else:
                pp = self._pre_pedido_repo.get_by_origem_sistema_id(str(order_code))

            if not pp:
                logger.warning(
                    "[OBSERVER-SUB] ⚠ PrePedido não encontrado para order_code=%s — skip confirm",
                    order_code,
                )
                return

            flag = _ACTION_FLAG_MAP.get(action)
            if flag:
                setattr(pp, flag, True)
                self._pre_pedido_repo.update(pp)
                logger.info(
                    "[OBSERVER-SUB] ✔ Marcado %s=True | pre_pedido.id=%d", flag, pp.id,
                )

        except Exception as exc:
            logger.error(
                "[OBSERVER-SUB] ❌ Falha ao marcar entrega | action=%s | order_code=%s | %s",
                action.value, order_code, exc,
            )
