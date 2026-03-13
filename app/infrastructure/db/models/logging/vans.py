from sqlalchemy import Column, String, Integer, BigInteger, UUID, ForeignKey

from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from app.infrastructure.db import Base

from app.infrastructure.db.models.integrations.integrations import Integrations

class LogPrePedidosVansModels(Base, DefaultAttributesModel):
    __tablename__ = "log_pre_pedidos_vans"
    __table_args__ = {"schema": "logs"}

    id = Column(Integer, primary_key=True, index=True)
    pedido_van_id = Column(String(255), index=True)
    message_id = Column(BigInteger, index=True)
    log_uuid = Column(UUID, index=True)
    integration_id = Column(Integer, ForeignKey(Integrations.id, ondelete="CASCADE"), nullable=False)
    integration_status = Column(String(50), nullable=True)
