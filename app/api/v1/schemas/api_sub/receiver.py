"""
Módulo de schemas para API de subscrição.

Este módulo define os schemas Pydantic para recebimento de mensagens
do Google Cloud Pub/Sub.

Classes:
    PubSubAttributes: Atributos de uma mensagem Pub/Sub
    PubSubMessage: Mensagem do Pub/Sub
    PubSub: Payload completo recebido do Pub/Sub
"""

from pydantic import BaseModel
from typing import Optional
from pydantic import Field


class PubSubAttributes(BaseModel):
    """
    Atributos de metadados de uma mensagem Pub/Sub.

    Attributes:
        pub_id: ID único da publicação
        topic_id: ID do tópico de origem
        industrial_code: Código da indústria (opcional)
    """
    pub_id: str = Field(..., description="ID do publicador")
    topic_id: str = Field(..., description="ID do tópico")
    industrial_code: Optional[str] = Field(None, description="Código da indústria")


class PubSubMessage(BaseModel):
    """
    Representa uma mensagem do Google Cloud Pub/Sub.

    Attributes:
        data: Conteúdo da mensagem codificado em base64
        messageId: ID único da mensagem gerado pelo Pub/Sub
        attributes: Atributos customizados da mensagem
    """
    data: str = Field(..., description="Dados da mensagem em base64")
    messageId: str = Field(..., description="ID da mensagem")
    attributes: PubSubAttributes


class PubSub(BaseModel):
    """
    Payload completo recebido de uma subscrição Pub/Sub.

    Este schema representa o formato padrão enviado pelo Google Cloud Pub/Sub
    para endpoints de push subscription.

    Attributes:
        subscription: Nome da subscrição que enviou a mensagem
        message: Objeto contendo a mensagem e seus metadados
    """
    subscription: str = Field(..., description="Nome da assinatura do Pub/Sub")
    message: PubSubMessage
