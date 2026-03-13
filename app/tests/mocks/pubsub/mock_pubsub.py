"""
Módulo de mock para Google Cloud Pub/Sub.

Este módulo fornece uma implementação mock do sistema Pub/Sub que simula
o comportamento completo de publicação e entrega de mensagens para testes locais.

Classes:
    Subscriber: Representa uma subscrição do Pub/Sub
    MockPubSubPublisher: Mock do publisher Pub/Sub

Variáveis:
    topics: Mapeamento de tópicos para seus subscritores
"""

from httpx import AsyncClient, ASGITransport
from app.domain.protocol.pubsub.pubsub import PubSubProtocol
from dataclasses import dataclass
from typing import List, Tuple, Callable
from app.api.v1.schemas.api_sub.receiver import PubSub, PubSubMessage, PubSubAttributes
from edwh_uuid7 import uuid7
from main import app
from app.core.dependencies import get_example_integration, get_datasul_service
import base64
import time
import logging


@dataclass
class Subscriber:
    """
    Representa um subscritor de um tópico Pub/Sub.

    Attributes:
        subscription: Nome da subscrição
        url: URL do endpoint que receberá as mensagens
        dependency: Factory de dependências para o endpoint
    """
    subscription: str
    url: str
    dependency: Callable[[], any]


# Configuração de tópicos e subscritores para testes
topics: dict[str, List[Subscriber]] = {
    "topic_1": [
        Subscriber(
            subscription="sub_1",
            url="/sub/example-subscribe-message",
            dependency=get_example_integration
        ),
    ],
    "vans_pre_pedido_datasul": [
        Subscriber(
            subscription="vans_sub_pre_pedido_datasul",
            url="/datasul-subscribe/pre-pedido-datasul",
            dependency=get_datasul_service
        ),
    ]
}


class MockPubSubPublisher(PubSubProtocol):
    """
    Mock do Google Cloud Pub/Sub para testes.

    Esta classe simula o comportamento completo do Pub/Sub, incluindo:
    - Publicação de mensagens
    - Entrega automática para subscritores
    - Geração de IDs de mensagem
    - Codificação base64 de payloads

    O mock permite testar fluxos completos de pub/sub sem necessidade
    de configuração do GCP.
    """

    @staticmethod
    def _generate_fake_pubsub_id():
        """
        Gera um ID único para a mensagem Pub/Sub.

        Returns:
            str: Timestamp em nanosegundos como string
        """
        return str(time.time_ns())

    def _build_pubsub_messages(self, topic: str, message: str, attributes: dict) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Constrói as mensagens Pub/Sub para todos os subscritores de um tópico.

        Este método:
        1. Codifica a mensagem em base64
        2. Gera IDs únicos (message_id e pub_id)
        3. Cria payloads no formato Pub/Sub para cada subscritor

        Args:
            topic: Nome do tópico
            message: Conteúdo da mensagem (será codificado em base64)
            attributes: Atributos customizados da mensagem

        Returns:
            Tuple[str, List[Tuple[str, str]]]: Tupla contendo:
                - message_id gerado
                - Lista de tuplas (url, payload) para cada subscritor

        Raises:
            ValueError: Se não houver subscritores para o tópico
        """
        b64message = str(base64.b64encode(message.encode()))

        subscriptions = topics.get(topic, [])
        message_id = self._generate_fake_pubsub_id()
        pub_id = str(uuid7())

        list_to_send: List[Tuple[str, str]] = []

        if not subscriptions:
            raise ValueError(f"No subscribers found for topic: {topic}")

        for subscriber in subscriptions:
            schema = PubSub(
                subscription=subscriber.subscription,
                message=PubSubMessage(
                    data=b64message,
                    messageId=message_id,
                    attributes=PubSubAttributes(
                        pub_id=pub_id,
                        topic_id=topic,
                        industrial_code=attributes.get("industrial_code")
                    )
                )
            )
            list_to_send.append((subscriber.url, schema.model_dump()))

        return message_id, list_to_send

    async def publish_message(self, topic: str, message: str, attributes: dict):
        """
        Publica uma mensagem e a entrega automaticamente aos subscritores.

        Este método simula o comportamento do Pub/Sub:
        1. Cria a mensagem com IDs únicos
        2. Envia HTTP POST para cada subscritor do tópico
        3. Registra o status das entregas em logs

        Args:
            topic: Nome do tópico onde publicar
            message: Conteúdo da mensagem
            attributes: Atributos customizados

        Returns:
            str: ID da mensagem publicada

        Note:
            Ao contrário do Pub/Sub real, este mock entrega as mensagens
            de forma síncrona e imediata.
        """
        logging.debug(f"Mock publish to topic: {topic} with message: {message} and attributes: {attributes}")
        message_id, list_to_send = self._build_pubsub_messages(topic, message, attributes)

        for url, payload in list_to_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
                response = await client.post(url=url, json=payload)
                logging.info(f"Mock publish {url} response: {response.status_code}")

        return message_id

    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        """
        Mock da validação de token Pub/Sub.

        Args:
            token: Token JWT a validar
            email: Email esperado
            aud: Audience esperada

        Returns:
            bool: Resultado da validação (delega ao protocolo pai)
        """
        return super().validate_pubsub_token(token, email, aud)

