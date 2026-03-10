from sqlalchemy.orm import Session
from app.domain.protocol.integrations.repository import IntegrationsRepositoryProtocol

class AuthLoader:

    def __init__(self, auth_repository: IntegrationsRepositoryProtocol, db: Session):
        self.auth_repository = auth_repository
        self.db = db

    def load(self, integration_name: str):
        integration_data = self.auth_repository.get_by_name_with_auth(name=integration_name)
