"""
Repositório de AuthProvider.
Os campos sensíveis password e token são criptografados automaticamente
ao salvar e descriptografados ao recuperar, usando a SECRET_KEY configurada.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.infrastructure.db.models.integrations.auth_provider import AuthProvider
from app.domain.protocol.integrations.repository import AuthProviderRepositoryProtocol
from app.core.security import encrypt_value, decrypt_value
class AuthProviderRepository(AuthProviderRepositoryProtocol):
    """
    Repositório para persistência de AuthProvider no PostgreSQL.
    Garante que password e token sejam armazenados criptografados
    e retornados descriptografados de forma transparente.
    """
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Helpers de criptografia
    # ------------------------------------------------------------------
    @staticmethod
    def _encrypt_sensitive_fields(auth_provider: AuthProvider) -> None:
        """Criptografa password e token in-place antes de persistir."""
        if auth_provider.password:
            auth_provider.password = encrypt_value(auth_provider.password)
        if auth_provider.token:
            auth_provider.token = encrypt_value(auth_provider.token)

    @staticmethod
    def _decrypt_sensitive_fields(auth_provider: AuthProvider) -> AuthProvider:
        """Descriptografa password e token após recuperar do banco."""
        if auth_provider.password:
            auth_provider.password = decrypt_value(auth_provider.password)
        if auth_provider.token:
            auth_provider.token = decrypt_value(auth_provider.token)
        return auth_provider

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def get_all(self) -> list[AuthProvider]:
        providers = self._db.query(AuthProvider).all()
        return [self._decrypt_sensitive_fields(p) for p in providers]

    def get_by_id(self, auth_provider_id: str) -> Optional[AuthProvider]:
        provider = self._db.query(AuthProvider).filter(
            AuthProvider.id == auth_provider_id
        ).first()
        if provider:
            return self._decrypt_sensitive_fields(provider)
        return None

    def get_by_integration_id(self, integration_id: int) -> Optional[AuthProvider]:
        provider = self._db.query(AuthProvider).filter(
            AuthProvider.integration_id == integration_id
        ).first()
        if provider:
            return self._decrypt_sensitive_fields(provider)
        return None

    def create(self, auth_provider: AuthProvider) -> AuthProvider:
        self._encrypt_sensitive_fields(auth_provider)
        self._db.add(auth_provider)
        self._db.commit()
        self._db.refresh(auth_provider)
        return self._decrypt_sensitive_fields(auth_provider)

    def update(self, auth_provider: AuthProvider) -> AuthProvider:
        self._encrypt_sensitive_fields(auth_provider)
        merged = self._db.merge(auth_provider)
        self._db.commit()
        self._db.refresh(merged)
        return self._decrypt_sensitive_fields(merged)

    def delete(self, auth_provider_id: str) -> None:
        provider = self._db.query(AuthProvider).filter(
            AuthProvider.id == auth_provider_id
        ).first()
        if provider is not None:
            provider.status = False
            self._db.commit()
