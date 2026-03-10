from app.domain.entities.auth.auth_provider import AuthEntity
from dataclasses import dataclass


@dataclass
class AuthLoaderEntity:
    integration_name: str
    auth: AuthEntity
