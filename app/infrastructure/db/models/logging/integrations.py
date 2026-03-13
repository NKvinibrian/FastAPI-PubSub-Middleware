from sqlalchemy import Column, Index, Integer, String, UUID, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.db import Base

class IntegrationLogs(Base):
    __tablename__ = 'integration_logs'
    __table_args__ = (Index('log_idx_uuid','log_uuid'),
        {"schema": "logs"})
    id = Column(Integer, primary_key=True, comment='Identificador do log')
    log_uuid = Column(UUID, comment='UUID do Log', nullable=True)
    origin_system = Column(String, comment='Sistema de origem: Fidelize Funcional / Interplayers', nullable=True)
    component_name = Column(String, comment='fetcher, parser,observer', nullable=True)
    process_name = Column(String, comment='Classe que está executando o processo', nullable=True)
    message_text = Column(String, comment='Mensagem do log', nullable=True)
    file_path = Column(String, comment='Caminho do arquivo no bucket para TXT', nullable=True)
    response_json = Column(JSONB, comment='JSON com pré-pedidos', nullable=True)
    file_type = Column(String, comment='Tipo do arquivo: txt / json', nullable=True)
    error_details = Column(String, comment='Descrição do erro', nullable=True)
    created_at = Column(TIMESTAMP, comment='Data de criação do log', nullable=True)
    started_at = Column(TIMESTAMP, comment='Data de início do processamento', nullable=True)
    finished_at = Column(TIMESTAMP, comment='Data de término do processamento', nullable=True)
    duration_ms = Column(Integer, comment='Duração do processamento em milissegundos', nullable=True)
    updated_at = Column(TIMESTAMP, comment='Data da última atualização do log', nullable=True)
    status = Column(String, comment='Status do processamento: SUCCESS, FAILED, STARTED, IN_PROGRESS', nullable=True)
