from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.infrastructure.auth.loader import AuthLoader
from app.infrastructure.auth.context import AuthContext
from app.infrastructure.repositories.integrations.integrations import IntegrationsRepository


@dataclass
class VanAuthContext:
    integration_name: str
    integration_id: int
    auth: AuthContext
    db: Session


class SetupContext:

    def __init__(self, db: Session) -> None:
        self._db = db

    def load(self, integration_name: str) -> VanAuthContext:
        repository = IntegrationsRepository(db=self._db)
        loader = AuthLoader(auth_repository=repository)
        auth_context = loader.load(integration_name)

        integration_entity = repository.get_by_name(integration_name)
        integration_id = integration_entity.id if integration_entity else 0

        return VanAuthContext(
            integration_name=integration_name,
            integration_id=integration_id,
            auth=auth_context,
            db=self._db,
        )
