from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.db import Base
from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from app.infrastructure.db.models.integrations.integrations import Integrations

class AuthProvider(Base, DefaultAttributesModel):
    """
    Modelo de provedor de autenticação.
    Este modelo representa os provedores de autenticação disponíveis no sistema.
    """
    __tablename__ = "auth_providers"
    __table_args__ = (
        {"schema": "hub"}
    )

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(ForeignKey(Integrations.id, ondelete="CASCADE"), nullable=False)
    auth_endpoint = Column(String(255), nullable=False)

    # Case Login credentials
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)

    # Case Token for authentication
    token = Column(String(255), nullable=True)

    # Case GraphQL endpoint for authentication
    mutation = Column(String(255), nullable=True)

    # Type of authentication (e.g., "basic", "token", "graphql", "FTP")
    auth_type = Column(String(50), nullable=False)

    # Type of response expected from the authentication endpoint (e.g., "json", "xml")
    response_type = Column(String(50), nullable=False)

    # Field to extract the token from the response (e.g., "access_token")
    token_field = Column(String(255), nullable=True)

    # Headers to include in the authentication request (e.g., {"Content-Type": "application/json"})
    headers = Column(JSONB, nullable=True)

    # Request method to use for authentication (e.g., "POST", "GET")
    request_method = Column(String(10), nullable=False)

    def __repr__(self):
        return f"<AuthProvider(id={self.id}, integration_id='{self.integration_id}')>"
