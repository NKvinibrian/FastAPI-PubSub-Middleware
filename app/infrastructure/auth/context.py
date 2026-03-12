from dataclasses import dataclass
from app.domain.protocol.auth.auth_provider import AuthProviderProtocol


@dataclass
class AuthContext:
    integration_name: str
    base_url: str
    timeout: int
    type_api: str
    provider: AuthProviderProtocol

