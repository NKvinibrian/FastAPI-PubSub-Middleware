from fastapi.testclient import TestClient
from main import app
from app.tests.mocks.pubsub.mock_pubsub import MockPubSubPublisher
from app.core.depedencies import get_pubsub
from app.api.v1.schemas.api_pub.sender import SenderSchema
import logging
from faker import Faker
from httpx import AsyncClient, ASGITransport

import pytest

logging.basicConfig(level=logging.INFO)
fake = Faker()

def _generate_random_message():
    message = SenderSchema(
        name=fake.name(),
        email=fake.email(),
        message=fake.text(),
    )
    return message.model_dump()


@pytest.mark.asyncio
async def test_pubsub_example():
    app.dependency_overrides[get_pubsub] = lambda: MockPubSubPublisher()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
        response = await client.post(
            url="/pub/example-publish-message",
            json=_generate_random_message()
        )
        print(response.status_code)
        assert response.status_code == 201
        print(response.json())
