"""
Schemas Pydantic genéricos para pré-pedidos de VANs.

Estes schemas representam o formato universal de saída de qualquer VAN
(Fidelize, Interplayers, IQVIA, etc.) após o parsing.

São usados para:
- Validar/serializar dados antes de salvar no banco
- Publicar no PubSub (um pedido por vez)
- Trafegar entre camadas (parser → pubsub → job)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PrePedidoItemSchema(BaseModel):
    """Item de um pré-pedido (produto)."""

    ean: str = Field(..., description="Código EAN do produto")
    amount: int = Field(..., description="Quantidade solicitada")
    gross_value: Optional[float] = Field(None, description="Valor bruto unitário")
    discount_percentage: Optional[float] = Field(None, description="Percentual de desconto")
    net_value: Optional[float] = Field(None, description="Valor líquido unitário")
    monitored: bool = Field(False, description="Se o produto é monitorado")
    payment_term: Optional[str] = Field(None, description="Prazo de pagamento do item")


class PrePedidoSchema(BaseModel):
    """
    Schema genérico de pré-pedido para todas as VANs.

    Representa UM pedido completo com seus itens.
    O PubSub publica um PrePedidoSchema por mensagem.
    """

    # Identificadores
    order_code: str = Field(..., description="Código do pedido na VAN (ex: order_code da Fidelize)")
    origin_system_id: str = Field(..., description="ID interno do pedido no sistema de origem")
    origin_system: str = Field(..., description="Nome do sistema de origem (ex: Fidelize Funcional Wholesaler)")

    # Indústria
    industry_code: str = Field(..., description="Código da indústria/projeto (ex: FAB, SAN)")

    # Cliente
    customer_code: Optional[str] = Field(None, description="Código do cliente (CNPJ/CPF)")
    customer_alternative_code: Optional[str] = Field(None, description="Código alternativo do cliente")
    customer_email: Optional[str] = Field(None, description="Email do cliente")
    customer_code_type: Optional[str] = Field(None, description="Tipo do código do cliente")

    # Distribuidor
    wholesaler_code: Optional[str] = Field(None, description="CNPJ do distribuidor")
    wholesaler_branch_code: Optional[str] = Field(None, description="CNPJ da filial do distribuidor")

    # Pedido
    status: Optional[str] = Field(None, description="Status do pedido na VAN")
    notification_obs: Optional[str] = Field(None, description="Observações de notificação")
    notification_status: Optional[str] = Field(None, description="Status de notificação")
    order_payment_term: Optional[str] = Field(None, description="Prazo de pagamento do pedido")
    commercial_condition_code: Optional[str] = Field(None, description="Código da condição comercial")
    additional_information: Optional[str] = Field(None, description="Informações adicionais")
    scheduled_delivery_order: Optional[bool] = Field(None, description="Se é entrega programada")

    # Datas
    tradetools_created_at: Optional[datetime] = Field(None, description="Data de criação no sistema VAN")

    # Itens
    products: list[PrePedidoItemSchema] = Field(default_factory=list, description="Itens do pedido")

