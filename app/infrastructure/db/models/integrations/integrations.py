from app.infrastructure.db import Base
from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from sqlalchemy import Column, Integer, String, Time, BOOLEAN


class Integrations(Base, DefaultAttributesModel):
    __tablename__ = "integrations"
    __table_args__ = (
        {"schema": "hub"}
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    type_api = Column(String(50), nullable=False)
    base_url = Column(String(100), nullable=False)
    timeout = Column(Time, nullable=False, default=500)

    # If true, will use a generic fetcher
    generic_fetcher = Column(BOOLEAN, nullable=False, default=False)