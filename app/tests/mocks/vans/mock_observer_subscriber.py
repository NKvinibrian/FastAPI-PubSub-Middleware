"""
Mock do ObserverSubscriberService para testes.

Simula o envio à VAN com sucesso (sem HTTP real) e executa
o restante do fluxo normalmente:
    1. Decodifica a mensagem
    2. Finge enviar para a VAN → armazena em sent_messages
    3. Marca os flags no pre_pedido (DB real via PrePedidoRepository)

Segue o mesmo padrão do MockDatasulService: fake na parte externa,
real na persistência.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.schemas.vans.observer_message import ObserverAction, ObserverMessageSchema
from app.domain.services.vans.observer_subscriber_service import (
    ACTION_TO_REQUEST_NAME,
    _ACTION_FLAG_MAP,
)
from app.infrastructure.repositories.vans.pre_pedidos import PrePedidoRepository

logger = logging.getLogger(__name__)


class MockObserverSubscriberService:
    """
    Mock do ObserverSubscriberService que simula envio à VAN.

    Em vez de fazer HTTP real, armazena as mensagens enviadas
    em `sent_messages` para assertions e executa o `_mark_as_delivered`
    real no banco.

    Attributes:
        sent_messages: Lista de mensagens "enviadas" (para assertions nos testes).
    """

    def __init__(self, db: Session, **kwargs) -> None:
        self._db = db
        self._pre_pedido_repo = PrePedidoRepository(db=db)
        self.sent_messages: list[dict[str, Any]] = []

    async def process(self, message: ObserverMessageSchema) -> dict:
        """
        Processa a mensagem simulando envio à VAN com sucesso.

        Fluxo:
            1. Valida action e request_name
            2. Simula envio (armazena em sent_messages)
            3. Marca pre_pedido como entregue (DB real)
        """
        action = message.action
        order_code = message.setup.query_parameters.get("order_code", "?")
        request_name = ACTION_TO_REQUEST_NAME.get(action)

        logger.info(
            "[MOCK-OBSERVER-SUB] 📩 Recebido | action=%s | integration=%s | order_code=%s",
            action.value, message.integration, order_code,
        )

        if not request_name:
            logger.error("[MOCK-OBSERVER-SUB] ❌ Action desconhecida: %s", action.value)
            return {"status": "error", "detail": f"Unknown action: {action.value}"}

        # ── Simula envio à VAN (sucesso) ────────────────────────────────
        self.sent_messages.append({
            "action": action.value,
            "order_code": order_code,
            "integration": message.integration,
            "integration_id": message.integration_id,
            "payload": message.payload,
        })

        logger.info(
            "[MOCK-OBSERVER-SUB] ✔ Envio simulado com sucesso | action=%s | order_code=%s",
            action.value, order_code,
        )

        # ── Marca pré-pedido como entregue (DB real) ────────────────────
        self._mark_as_delivered(action, message.payload, order_code)

        return {
            "status": "ok",
            "action": action.value,
            "order_code": order_code,
            "van_status": 200,
        }

    def _mark_as_delivered(
        self,
        action: ObserverAction,
        payload: dict,
        order_code: str,
    ) -> None:
        """
        Marca o pré-pedido como entregue no banco.

        Mesma lógica do service real — usa PrePedidoRepository.
        """
        try:
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
                    "[MOCK-OBSERVER-SUB] ⚠ PrePedido não encontrado para order_code=%s — skip confirm",
                    order_code,
                )
                return

            flag = _ACTION_FLAG_MAP.get(action)
            if flag:
                setattr(pp, flag, True)
                self._pre_pedido_repo.update(pp)
                logger.info(
                    "[MOCK-OBSERVER-SUB] ✔ Marcado %s=True | pre_pedido.id=%d",
                    flag, pp.id,
                )

        except Exception as exc:
            logger.error(
                "[MOCK-OBSERVER-SUB] ❌ Falha ao marcar entrega | action=%s | order_code=%s | %s",
                action.value, order_code, exc,
            )
