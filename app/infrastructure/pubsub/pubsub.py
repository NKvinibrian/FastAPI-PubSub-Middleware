from app.domain.protocol.pubsub.pubsub import PubSubProtocol


class PubSubPublisher(PubSubProtocol):

    def publish_message(self, topic: str, message: str, attributes: dict):
        raise NotImplementedError('Method not implemented')

    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        raise NotImplementedError('Method not implemented')
