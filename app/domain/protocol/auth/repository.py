"""
Módulo de protocolo para o repositório de AuthProvider.

Define o contrato (interface) que deve ser implementado pelo
repositório de AuthProvider.

Classes:
    AuthRepositoryProtocol: Protocolo para o repositório de autenticação.
"""

from typing import Protocol, Optional
from app.domain.entities.auth.auth import AuthEntity


class AuthRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de AuthProvider."""

    def get_all(self) -> list[AuthEntity]:
        """Retorna todos os provedores de autenticação cadastrados."""
        ...

    def get_by_id(self, auth_id: str) -> Optional[AuthEntity]:
        """Busca um provedor de autenticação pelo ID."""
        ...

    def get_by_integration_id(self, integration_id: str) -> Optional[AuthEntity]:
        """Busca um provedor de autenticação pelo integration_id."""
        ...

    def create(self, auth: AuthEntity) -> AuthEntity:
        """Cria um novo provedor de autenticação."""
        ...

    def update(self, auth: AuthEntity) -> AuthEntity:
        """Atualiza um provedor de autenticação existente."""
        ...

    def delete(self, auth_id: str) -> None:
        """Remove um provedor de autenticação pelo ID."""
        ...

