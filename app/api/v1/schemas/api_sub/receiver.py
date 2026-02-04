from pydantic import BaseModel
from typing import Optional
from pydantic import Field

class PubSubAttributes(BaseModel):
    pub_id: str = Field(..., description="ID do publicador")
    topic_id: str = Field(..., description="ID do tópico")
    industrial_code: Optional[str] = Field(None, description="Código da indústria")


class PubSubMessage(BaseModel):
    data: str = Field(..., description="Dados da mensagem em base64")
    messageId: str = Field(..., description="ID da mensagem")
    attributes: PubSubAttributes


class PubSub(BaseModel):
    subscription: str = Field(..., description="Nome da assinatura do Pub/Sub")
    message: PubSubMessage
