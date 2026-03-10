from dataclasses import dataclass
from app.domain.entities.auth.auth_provider import AuthEntity


@dataclass
class IntegrationEntity:
    id: int
    name: str
    type_api: str
    base_url: str
    timeout: int
    generic_fetcher: bool


@dataclass
class IntegrationWithAuthEntity(IntegrationEntity):
    auth: AuthEntity
