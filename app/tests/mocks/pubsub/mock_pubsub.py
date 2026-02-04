from httpx import AsyncClient, ASGITransport
from app.domain.protocol.pubsub.pubsub import PubSubProtocol
from dataclasses import dataclass
from typing import List, Tuple, Callable
from app.api.v1.schemas.api_sub.receiver import PubSub, PubSubMessage, PubSubAttributes
from edwh_uuid7 import uuid7
from main import app
from app.core.depedencies import get_example_integration
import base64
import time
import logging


@dataclass
class Subscriber:
    subscription: str
    url: str
    dependency: Callable[[], any]


topics: dict[str, List[Subscriber]] = {
    "topic_1": [
        Subscriber(subscription="sub_1", url="/sub/example-subscribe-message", dependency=get_example_integration),
    ]
}


class MockPubSubPublisher(PubSubProtocol):

    @staticmethod
    def _generate_fake_pubsub_id():
        return str(time.time_ns())


    def _build_pubsub_messages(self, topic: str, message: str, attributes: dict) -> Tuple[str, List[Tuple[str, str]]]:
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
        logging.debug(f"Mock publish to topic: {topic} with message: {message} and attributes: {attributes}")
        message_id, list_to_send = self._build_pubsub_messages(topic, message, attributes)

        for url, payload in list_to_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as client:
                response = await client.post(url=url, json=payload)
                logging.info(f"Mock publish {url} response: {response.status_code}")

        return message_id

    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        return super().validate_pubsub_token(token, email, aud)

