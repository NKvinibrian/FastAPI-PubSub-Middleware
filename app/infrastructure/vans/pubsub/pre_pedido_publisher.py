"""
Publisher genérico de pré-pedidos para PubSub.

Publica pedidos de QUALQUER VAN — recebe list[PrePedidoSchema]
e envia um pedido por mensagem. Atualiza o message_id no
LogPrePedidosVans após a publicação.

Este publisher é agnóstico à VAN de origem.
"""

from typing import Union
from uuid import UUID

from app.api.v1.schemas.vans.pre_pedido import PrePedidoSchema
from app.domain.protocol.logs.repository import LogPrePedidosVansRepositoryProtocol
from app.domain.protocol.pubsub.pubsub import PubSubProtocol


class PrePedidoPubSubPublisher:
    """
    Publisher genérico que envia pré-pedidos ao PubSub.

    Publica UM pedido por mensagem. Após publicar, atualiza
    o LogPrePedidosVans com o message_id retornado.

    Attributes:
        _pubsub: Cliente PubSub (implementa PubSubProtocol).
        _topic: Nome do tópico de destino.
        _log_repository: Repositório de LogPrePedidosVans.
    """

    def __init__(
        self,
        pubsub: PubSubProtocol,
        topic: str,
        log_repository: LogPrePedidosVansRepositoryProtocol,
    ) -> None:
        self._pubsub = pubsub
        self._topic = topic
        self._log_repository = log_repository

    async def publish(
        self,
        orders: list[PrePedidoSchema],
        log_uuid: UUID,
    ) -> list[Union[str, int]]:
        """
        Publica cada pedido individualmente no PubSub.

        Para cada pedido:
        1. Serializa como JSON
        2. Publica no tópico com attributes (origin_system, order_code, log_uuid)
        3. Atualiza o LogPrePedidosVans correspondente com o message_id

        Args:
            orders: Lista de pedidos parseados (um PrePedidoSchema por pedido).
            log_uuid: UUID do grupo de processamento.

        Returns:
            Lista de message_ids retornados pelo PubSub.
        """
        message_ids: list[Union[str, int]] = []

        for order in orders:
            message = order.model_dump_json()

            attributes = {
                "origin_system": order.origin_system,
                "order_code": order.order_code,
                "industry_code": order.industry_code,
                "log_uuid": str(log_uuid),
            }

            message_id = await self._pubsub.publish_message(
                topic=self._topic,
                message=message,
                attributes=attributes,
            )

            # Atualiza o log do pedido com o message_id
            logs = self._log_repository.get_by_pedido_van_id(order.order_code)
            for log in logs:
                if log.log_uuid == log_uuid and log.message_id is None:
                    log.message_id = int(message_id) if isinstance(message_id, str) and message_id.isdigit() else message_id
                    log.integration_status = "PUBLISHED"
                    self._log_repository.update(log)
                    break

            message_ids.append(message_id)

        return message_ids

