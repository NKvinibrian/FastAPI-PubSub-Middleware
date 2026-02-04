from pydantic import BaseModel, Field

class SenderSchema(BaseModel):
    name: str = Field(None, description="Nome do remetente")
    email: str = Field(None, description="Email do remetente")
    message: str = Field(None, description="Mensagem do remetente")
