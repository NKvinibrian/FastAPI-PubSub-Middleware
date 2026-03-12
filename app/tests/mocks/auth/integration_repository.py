"""
Mock do repositório de integrações para uso nos testes de AuthLoader.

Simula o retorno de `get_by_name_with_auth` sem tocar no banco de dados,
permitindo testar cada auth_type de forma isolada.
"""

from typing import Optional
from app.domain.entities.auth.auth_provider import AuthEntity
from app.domain.entities.integrations.integration import IntegrationWithAuthEntity


def _make_integration(auth: AuthEntity) -> IntegrationWithAuthEntity:
    return IntegrationWithAuthEntity(
        id=1,
        name=auth.integration_id,
        type_api="REST",
        base_url="https://api.example.com",
        timeout=30,
        generic_fetcher=False,
        auth=auth,
    )


def _base_auth(**kwargs) -> AuthEntity:
    defaults = dict(
        id="auth-001",
        integration_id="test-integration",
        auth_endpoint="https://api.example.com/auth",
        auth_type="basic",
        response_type="json",
        username="user",
        password="pass",
        token=None,
        mutation=None,
        token_field="access_token",
        headers=None,
    )
    defaults.update(kwargs)
    return AuthEntity(**defaults)


class MockIntegrationsRepository:
    """
    Mock do IntegrationsRepositoryProtocol.
    Recebe o AuthEntity que deve ser devolvido por `get_by_name_with_auth`.
    """

    def __init__(self, auth: Optional[AuthEntity] = None):
        self._auth = auth

    def get_by_name_with_auth(self, name: str) -> Optional[IntegrationWithAuthEntity]:
        if self._auth is None:
            return None
        return _make_integration(self._auth)

    # ── stubs dos demais métodos do protocolo ────────────────────────────────
    def get_all(self):
        return []

    def get_by_id(self, integration_id: int):
        return None

    def create(self, integration):
        return integration

    def update(self, integration):
        return integration

    def delete(self, integration_id: int):
        pass

    def get_by_name(self, name: str):
        return None


# ── factories por auth_type ──────────────────────────────────────────────────

def make_basic_auth() -> AuthEntity:
    return _base_auth(auth_type="basic")


def make_body_auth() -> AuthEntity:
    return _base_auth(auth_type="body", response_type="json")


def make_graphql_auth() -> AuthEntity:
    return _base_auth(auth_type="graphql", mutation="createToken")


def make_bearer_auth() -> AuthEntity:
    return _base_auth(auth_type="bearer", token="my-static-token")


def make_token_auth() -> AuthEntity:
    return _base_auth(auth_type="token", token="my-static-token")

