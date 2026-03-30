"""
Publisher genérico do Observer para PubSub.

Publica mensagens de QUALQUER VAN — recebe list[ObserverMessageSchema]
e envia uma mensagem por item. Roteia para o tópico correto
usando o action da mensagem.

Funciona para os 4 fluxos:
  - ORDER_RETURN       → merco-observer-order-return
  - ORDER_RETURN_REJECTION → merco-observer-order-rejection
  - RETURN_INVOICES    → merco-observer-invoices
  - RETURN_CANCELLATION → merco-observer-cancellation
"""

import logging
from typing import Union
from uuid import UUID

from app.api.v1.schemas.vans.observer_message import ObserverAction, ObserverMessageSchema
from app.domain.protocol.pubsub.pubsub import PubSubProtocol

logger = logging.getLogger(__name__)


class ObserverPubSubPublisher:
    """
    Publisher genérico que envia mensagens do Observer ao PubSub.

    Publica UMA mensagem por item. Roteia para o tópico correto
    usando o mapeamento action → topic.

    Attributes:
        _pubsub: Cliente PubSub (implementa PubSubProtocol).
        _topic_map: Mapeia ObserverAction → nome do tópico PubSub.
    """

    def __init__(
        self,
        pubsub: PubSubProtocol,
        topic_map: dict[ObserverAction, str],
    ) -> None:
        self._pubsub = pubsub
        self._topic_map = topic_map

    async def publish(
        self,
        messages: list[ObserverMessageSchema],
        log_uuid: UUID,
    ) -> list[Union[str, int]]:
        """
        Publica cada mensagem individualmente no tópico correto.

        Args:
            messages: Lista de mensagens genéricas do Observer.
            log_uuid: UUID do grupo de processamento.

        Returns:
            Lista de message_ids retornados pelo PubSub.
        """
        message_ids: list[Union[str, int]] = []

        for msg in messages:
            topic = self._topic_map.get(msg.action)
            if not topic:
                logger.warning(
                    "[OBSERVER-PUB] ⚠ Tópico não configurado para action=%s — pulando",
                    msg.action.value,
                )
                continue

            body = msg.model_dump_json()

            attributes = {
                "integration": msg.integration,
                "integration_id": str(msg.integration_id),
                "action": msg.action.value,
                "check_id": msg.setup.check_id,
                "order_code": str(msg.setup.query_parameters.get("order_code", "")),
                "industry_code": str(msg.setup.query_parameters.get("industry_code", "")),
                "log_uuid": str(log_uuid),
            }

            message_id = await self._pubsub.publish_message(
                topic=topic,
                message=body,
                attributes=attributes,
            )

            logger.info(
                "[OBSERVER-PUB] ✔ Published %s | order_code=%s | topic=%s | msg_id=%s",
                msg.action.value,
                attributes["order_code"],
                topic,
                message_id,
            )

            message_ids.append(message_id)

        return message_ids

