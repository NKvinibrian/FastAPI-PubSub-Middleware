from typing import Protocol, Union


class PubSubProtocol(Protocol):

    async def publish_message(self, topic: str, message: str, attributes: dict) -> Union[str, int]:
        ...


    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        ...
