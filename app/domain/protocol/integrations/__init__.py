"""
Pacote de protocolos de integrations.
"""

from app.domain.protocol.integrations.repository import (
    IntegrationsRepositoryProtocol,
    AuthProviderRepositoryProtocol,
    RequestDetailsRepositoryProtocol,
)

__all__ = [
    "IntegrationsRepositoryProtocol",
    "AuthProviderRepositoryProtocol",
    "RequestDetailsRepositoryProtocol",
]

