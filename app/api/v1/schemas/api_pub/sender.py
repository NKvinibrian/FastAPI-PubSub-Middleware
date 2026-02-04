"""
Módulo de schemas para API de publicação.

Este módulo define os schemas Pydantic utilizados nos endpoints
de publicação de mensagens.

Classes:
    SenderSchema: Schema para dados do remetente de mensagens
"""

from pydantic import BaseModel, Field


class SenderSchema(BaseModel):
    """
    Schema para dados do remetente de mensagens.

    Attributes:
        name: Nome do remetente
        email: Email do remetente
        message: Conteúdo da mensagem a ser enviada
    """
    name: str = Field(None, description="Nome do remetente")
    email: str = Field(None, description="Email do remetente")
    message: str = Field(None, description="Mensagem do remetente")
