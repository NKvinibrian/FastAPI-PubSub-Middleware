"""
Publisher de desenvolvimento para Pub/Sub.

Usado quando MOCK_PUBSUB=true em ambiente de desenvolvimento/jobs standalone.
Não faz nenhuma chamada HTTP nem requer servidor FastAPI rodando.

Apenas loga a mensagem e retorna um message_id fake — suficiente para
rodar o fluxo completo do job em dev sem dependências externas.
"""

import logging
import time
from typing import Union

from app.domain.protocol.pubsub.pubsub import PubSubProtocol

logger = logging.getLogger(__name__)


class DevPubSubPublisher(PubSubProtocol):
    """
    Mock leve de PubSub para jobs standalone (sem servidor FastAPI).

    Registra cada mensagem no log e retorna um message_id baseado
    em timestamp. Não faz entrega HTTP — adequado para desenvolvimento
    e execução de jobs fora do contexto do servidor.
    """

    async def publish_message(
        self,
        topic: str,
        message: str,
        attributes: dict,
    ) -> Union[str, int]:
        """
        Simula a publicação sem fazer nenhuma chamada externa.

        Args:
            topic: Nome do tópico.
            message: Payload da mensagem (JSON string).
            attributes: Atributos da mensagem.

        Returns:
            str: message_id fake baseado em timestamp (nanosegundos).
        """
        message_id = str(time.time_ns())
        logger.info(
            "[DevPubSub] Published to '%s' | message_id=%s | order_code=%s",
            topic,
            message_id,
            attributes.get("order_code", "?"),
        )
        return message_id

    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        return True

