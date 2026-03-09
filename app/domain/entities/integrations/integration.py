from dataclasses import dataclass

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
    auth: str