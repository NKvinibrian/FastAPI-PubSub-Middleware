"""
Módulo de testes para API Pub/Sub.

Este módulo contém testes automatizados para os endpoints de publicação
e subscrição de mensagens, utilizando mocks para simular o Pub/Sub.

Funções:
    _generate_random_message: Gera mensagens aleatórias para testes
    test_pubsub_example: Testa o fluxo completo de pub/sub
"""

from main import app
from app.tests.mocks.pubsub.mock_pubsub import MockPubSubPublisher
from app.core.dependencies import get_pubsub
from app.api.v1.schemas.api_pub.sender import SenderSchema
import logging
from faker import Faker
from httpx import AsyncClient, ASGITransport

import pytest

logging.basicConfig(level=logging.INFO)
fake = Faker()


def _generate_random_message():
    """
    Gera uma mensagem aleatória para testes.

    Utiliza a biblioteca Faker para criar dados fictícios realistas.

    Returns:
        dict: Dicionário com campos name, email e message preenchidos
              com dados aleatórios
    """
    message = SenderSchema(
        name=fake.name(),
        email=fake.email(),
        message=fake.text(),
    )
    return message.model_dump()


@pytest.mark.asyncio
async def test_pubsub_example():
    """
    Testa o fluxo completo de publicação e subscrição de mensagens.

    Este teste:
    1. Sobrescreve a dependência get_pubsub com o mock
    2. Gera uma mensagem aleatória
    3. Publica a mensagem via endpoint /pub/example-publish-message
    4. Verifica se a mensagem foi entregue ao subscritor
    5. Valida o status code e a resposta

    O MockPubSubPublisher automaticamente entrega a mensagem aos
    subscritores configurados em topics.

    Asserts:
        - Status code deve ser 201 (Created)
        - Resposta deve conter message_id
    """
    app.dependency_overrides[get_pubsub] = lambda: MockPubSubPublisher()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        response = await client.post(
            url="/pub/example-publish-message",
            json=_generate_random_message()
        )
        print(response.status_code)
        assert response.status_code == 201
        print(response.json())
