from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.infrastructure.db import Base
from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from app.infrastructure.db.models.integrations.integrations import Integrations

class RequestDetails(Base, DefaultAttributesModel):
    __tablename__ = "request_details"
    __table_args__ = (
        {"schema": "hub"}
    )

    id = Column(String(255), primary_key=True, index=True)
    integration_id = Column(ForeignKey(Integrations.id, ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=True)

    request_type = Column(String(10), nullable=False)  # e.g., "GET", "POST"
    endpoint = Column(String(255), nullable=False)  # e.g., "/api/data"
    headers = Column(JSONB, nullable=True)  # e.g., {"Content-Type": "application/json"}
    request_method = Column(String(10), nullable=False)  # e.g., "POST", "GET"
