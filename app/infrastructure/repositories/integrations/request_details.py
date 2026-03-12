"""
Repositório de RequestDetails.
Implementa operações CRUD para o modelo RequestDetails utilizando
uma sessão SQLAlchemy síncrona.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.infrastructure.db.models import RequestDetails
from app.infrastructure.db.models.integrations.integrations_requests_details import RequestDetails
from app.domain.protocol.integrations.repository import RequestDetailsRepositoryProtocol


class RequestDetailsRepository(RequestDetailsRepositoryProtocol):
    """
    Repositório para persistência de RequestDetails no PostgreSQL.
    Attributes:
        _db: Sessão ativa do SQLAlchemy.
    """
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all(self) -> list[type[RequestDetails]]:
        return self._db.query(RequestDetails).all()

    def get_by_id(self, request_details_id: str) -> Optional[RequestDetails]:
        return self._db.query(RequestDetails).filter(
            RequestDetails.id == request_details_id
        ).first()

    def get_by_integration_id(self, integration_id: int) -> list[type[RequestDetails]]:
        return self._db.query(RequestDetails).filter(
            RequestDetails.integration_id == integration_id
        ).all()

    def create(self, request_details: RequestDetails) -> RequestDetails:
        self._db.add(request_details)
        self._db.commit()
        self._db.refresh(request_details)
        return request_details

    def update(self, request_details: RequestDetails) -> RequestDetails:
        merged = self._db.merge(request_details)
        self._db.commit()
        self._db.refresh(merged)
        return merged

    def delete(self, request_details_id: str) -> None:
        request_details = self.get_by_id(request_details_id)
        if request_details is not None:
            request_details.status = False
            self._db.commit()
