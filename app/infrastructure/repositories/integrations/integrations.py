"""
Repositório de Integrations.
Implementa operações CRUD para o modelo Integrations utilizando
uma sessão SQLAlchemy síncrona.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.auth.auth_provider import AuthEntity
# Entity
from app.domain.entities.integrations.integration import IntegrationEntity
from app.domain.entities.integrations.integration import IntegrationWithAuthEntity

# Models
from app.infrastructure.db.models.integrations.integrations import Integrations
from app.infrastructure.db.models.integrations.auth_provider import AuthProvider

# Protocols
from app.domain.protocol.integrations.repository import IntegrationsRepositoryProtocol



class IntegrationsRepository(IntegrationsRepositoryProtocol):
    """
    Repositório para persistência de Integrations no PostgreSQL.
    Attributes:
        _db: Sessão ativa do SQLAlchemy.
    """
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def __map_to_entity(integration: Integrations) -> IntegrationEntity:
        return IntegrationEntity(
            id=integration.id,
            name=integration.name,
            type_api=integration.type_api,
            base_url=integration.base_url,
            timeout=integration.timeout,
            generic_fetcher=integration.generic_fetcher
        )

    @staticmethod
    def __map_to_entity_with_auth(integration: Integrations, auth: AuthProvider) -> IntegrationWithAuthEntity:
        auth_entity = AuthEntity(
            id=auth.id,
            integration_id=auth.integration_id,
            auth_type=auth.auth_type,
            username=auth.username,
            password=auth.password,
            token=auth.token,
            auth_endpoint=auth.auth_endpoint,
            response_type=auth.response_type
        )
        integration = IntegrationWithAuthEntity(
            id=integration.id,
            name=integration.name,
            type_api=integration.type_api,
            base_url=integration.base_url,
            timeout=integration.timeout,
            generic_fetcher=integration.generic_fetcher,
            auth=auth_entity
        )
        return integration

    def get_all(self) -> list[IntegrationEntity]:
        results = self._db.scalars(select(Integrations)).all()
        return [self.__map_to_entity(item) for item in results]

    def get_by_id(self, integration_id: int) -> Optional[IntegrationEntity]:
        result = self._db.scalars(
            select(Integrations).where(Integrations.id == integration_id)
        ).first()
        if result is None:
            return None
        return self.__map_to_entity(result)

    def create(self, integration: IntegrationEntity) -> IntegrationEntity:
        self._db.add(integration)
        self._db.commit()
        self._db.refresh(integration)
        return integration

    def update(self, integration: IntegrationEntity) -> IntegrationEntity:
        merged = self._db.merge(integration)
        self._db.commit()
        self._db.refresh(merged)
        return merged

    def delete(self, integration_id: int) -> None:
        result = self._db.scalars(
            select(Integrations).where(Integrations.id == integration_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()

    def get_by_name(self, name: str) -> Optional[IntegrationEntity]:
        result = self._db.scalars(
            select(Integrations).where(Integrations.name == name)
        ).first()
        if result is None:
            return None
        return self.__map_to_entity(result)

    def get_by_name_with_auth(self, name: str) -> Optional[IntegrationWithAuthEntity]:
        stmt = (
            select(Integrations, AuthProvider)
            .join(AuthProvider, AuthProvider.integration_id == Integrations.id)
            .where(Integrations.name == name)
        )
        row = self._db.execute(stmt).first()
        if row is None:
            return None
        integration_result, auth_result = row
        return self.__map_to_entity_with_auth(integration=integration_result, auth=auth_result)
