from sqlalchemy import Column, DateTime, Boolean, func


class DefaultAttributesModel:
    __abstract__ = True

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    status = Column(Boolean, default=True, nullable=False)
