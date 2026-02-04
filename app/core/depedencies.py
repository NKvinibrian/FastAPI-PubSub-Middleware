from app.domain.protocol.pubsub.pubsub import PubSubProtocol
from app.infrastructure.pubsub.pubsub import PubSubPublisher

from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol
from app.domain.services.integration_example.integration import ExampleIntegrationService

from app.infrastructure.repositories.logging.mongo import MongoLoggingRepository
from app.core.logging.logger import MongoLoggingService

from app.core import mongo

def get_pubsub() -> PubSubProtocol:
    return PubSubPublisher()

def get_example_integration() -> ExampleIntegrationProtocol:
    return ExampleIntegrationService()

def get_logging_repository():
    return MongoLoggingRepository(mongo.db, collection_name="logs")

def get_logging_service():
    logging_repository = get_logging_repository()
    return MongoLoggingService(logging_repository)
