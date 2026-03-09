from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthEntity:
    id: str
    integration_id: str
    auth_endpoint: str
    auth_type: str
    response_type: str
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    mutation: Optional[str] = None
    token_field: Optional[str] = None
    headers: Optional[dict] = None
