"""
Módulo de protocolos para repositórios de integrations.

Define os contratos (interfaces) que devem ser implementados pelos
repositórios de Integrations, AuthProvider e RequestDetails.

Classes:
    IntegrationsRepositoryProtocol: Protocolo para o repositório de integrações.
    AuthProviderRepositoryProtocol: Protocolo para o repositório de provedores de autenticação.
    RequestDetailsRepositoryProtocol: Protocolo para o repositório de detalhes de requisições.
"""

from typing import Protocol, Optional
from app.infrastructure.db.models.integrations.integrations import Integrations
from app.infrastructure.db.models.integrations.auth_provider import AuthProvider
from app.infrastructure.db.models.integrations.integrations_requests_details import RequestDetails
from app.domain.entities.integrations.integration import IntegrationEntity, IntegrationWithAuthEntity


class IntegrationsRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de Integrations."""

    def get_all(self) -> list[IntegrationEntity]:
        """Retorna todas as integrações cadastradas."""
        ...

    def get_by_id(self, integration_id: int) -> Optional[IntegrationEntity]:
        """Busca uma integração pelo ID."""
        ...

    def create(self, integration: IntegrationEntity) -> IntegrationEntity:
        """Cria uma nova integração."""
        ...

    def update(self, integration: IntegrationEntity) -> IntegrationEntity:
        """Atualiza uma integração existente."""
        ...

    def delete(self, integration_id: int) -> None:
        """Remove uma integração pelo ID."""
        ...

    def get_by_name(self, name: str) -> Optional[IntegrationEntity]:
        """Busca uma integração pelo nome."""
        ...

    def get_by_name_with_auth(self, name: str) -> Optional[IntegrationWithAuthEntity]:
        """Busca uma integração pelo nome, incluindo os dados de autenticação."""
        ...


class AuthProviderRepositoryProtocol(Protocol):
    """
    Protocolo para operações CRUD de AuthProvider.

    Senhas e tokens são armazenados criptografados e retornados
    descriptografados de forma transparente.
    """

    def get_all(self) -> list[AuthProvider]:
        """Retorna todos os provedores de autenticação."""
        ...

    def get_by_id(self, auth_provider_id: str) -> Optional[AuthProvider]:
        """Busca um provedor de autenticação pelo ID."""
        ...

    def get_by_integration_id(self, integration_id: int) -> Optional[AuthProvider]:
        """Busca o provedor de autenticação de uma integração específica."""
        ...

    def create(self, auth_provider: AuthProvider) -> AuthProvider:
        """
        Cria um novo provedor de autenticação.

        Criptografa password e token antes de persistir.
        """
        ...

    def update(self, auth_provider: AuthProvider) -> AuthProvider:
        """
        Atualiza um provedor de autenticação existente.

        Criptografa password e token antes de persistir.
        """
        ...

    def delete(self, auth_provider_id: str) -> None:
        """Remove um provedor de autenticação pelo ID."""
        ...


class RequestDetailsRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de RequestDetails."""

    def get_all(self) -> list[type[RequestDetails]]:
        """Retorna todos os detalhes de requisições."""
        ...

    def get_by_id(self, request_details_id: str) -> Optional[RequestDetails]:
        """Busca detalhes de requisição pelo ID."""
        ...

    def get_by_integration_id(self, integration_id: int) -> list[type[RequestDetails]]:
        """Retorna todos os detalhes de requisição de uma integração."""
        ...

    def create(self, request_details: RequestDetails) -> RequestDetails:
        """Cria um novo detalhe de requisição."""
        ...

    def update(self, request_details: RequestDetails) -> RequestDetails:
        """Atualiza um detalhe de requisição existente."""
        ...

    def delete(self, request_details_id: str) -> None:
        """Remove um detalhe de requisição pelo ID."""
        ...

