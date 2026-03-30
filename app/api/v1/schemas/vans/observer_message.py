"""
Schemas genéricos para mensagens do Observer PubSub.

O Observer é o fluxo REVERSO: envia dados de volta para as VANs
(retorno de pedidos, rejeições, notas fiscais, cancelamentos).

A mensagem é genérica — funciona para TODAS as VANs. O subscriber
usa o campo `integration` + `action` para rotear para a VAN correta.

Formato da mensagem:
{
    "integration": "Fidelize Funcional Wholesaler",
    "action": "ORDER_RETURN",
    "setup": {
        "check_id": "order_code",
        "query_parameters": {
            "order_code": "5001",
            "industry_code": "SAN"
        }
    },
    "payload": { ... dados específicos da mutation ... }
}
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ObserverAction(str, Enum):
    """As 4 ações do Observer — cada uma mapeia para um tópico PubSub."""

    ORDER_RETURN = "ORDER_RETURN"
    ORDER_RETURN_REJECTION = "ORDER_RETURN_REJECTION"
    RETURN_INVOICES = "RETURN_INVOICES"
    RETURN_CANCELLATION = "RETURN_CANCELLATION"


class ObserverSetupSchema(BaseModel):
    """
    Metadados para o subscriber identificar e rotear a mensagem.

    Attributes:
        check_id: Nome do campo chave para idempotência (ex: "order_code").
        query_parameters: Parâmetros que identificam o pedido na VAN.
    """

    check_id: str = Field(..., description="Campo-chave para idempotência (ex: order_code)")
    query_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parâmetros de identificação (ex: order_code, industry_code)",
    )


class ObserverMessageSchema(BaseModel):
    """
    Envelope genérico de uma mensagem do Observer.

    Uma mensagem = um pedido/NF para UMA action.
    O subscriber consome a mensagem e chama a API correta da VAN.
    """

    integration: str = Field(..., description="Nome da integração de origem (ex: Fidelize Funcional Wholesaler)")
    integration_id: int = Field(..., description="ID da integração no banco (FK para request_details)")
    action: ObserverAction = Field(..., description="Tipo da ação do observer")
    setup: ObserverSetupSchema = Field(..., description="Metadados de roteamento e idempotência")
    payload: dict[str, Any] = Field(..., description="Dados para a mutation/API da VAN")


# ═══════════════════════════════════════════════════════════════════════
#  Payload sub-schemas (validação opcional no publish)
# ═══════════════════════════════════════════════════════════════════════

class ObserverProductReturnSchema(BaseModel):
    """Produto no retorno de pedido (createResponse)."""

    ean: str
    response_amount: int
    unit_discount_percentage: float = 0.0
    unit_discount_value: float = 0.0
    unit_net_value: float = 0.0
    monitored: bool = False
    industry_consideration: Optional[str] = "000"


class OrderReturnPayload(BaseModel):
    """Payload para ORDER_RETURN e ORDER_RETURN_REJECTION."""

    industry_code: str
    order_code: int
    wholesaler_code: str
    wholesaler_order_code: Optional[str] = None
    payment_term: Optional[str] = None
    reason: str
    processed_at: str
    invoice_at: Optional[str] = None
    delivery_forecast_at: Optional[str] = None
    products: list[ObserverProductReturnSchema]


class ObserverProductInvoiceSchema(BaseModel):
    """Produto na nota fiscal (createInvoice)."""

    ean: str
    invoice_amount: int
    unit_discount_percentage: float = 0.0
    unit_discount_value: float = 0.0
    unit_net_value: float = 0.0


class InvoicePayload(BaseModel):
    """Payload para RETURN_INVOICES."""

    industry_code: str
    order_code: int
    wholesaler_code: str
    customer_code: str
    wholesaler_order_code: Optional[str] = None
    processed_at: str
    invoice_released_on: str
    invoice_code: str
    invoice_value: float
    invoice_discount: float
    invoice_danfe_key: str
    products: list[ObserverProductInvoiceSchema]


class ObserverProductCancellationSchema(BaseModel):
    """Produto no cancelamento (createCancellation)."""

    ean: str


class CancellationPayload(BaseModel):
    """Payload para RETURN_CANCELLATION."""

    order_code: int
    industry_code: str
    wholesaler_branch_code: str
    products: list[ObserverProductCancellationSchema]

