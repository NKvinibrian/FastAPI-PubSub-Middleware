"""
Módulo de modelos do banco de dados.

Importar todos os modelos aqui para que o Alembic possa detectá-los
automaticamente durante o autogenerate.
"""

from app.infrastructure.db.models.example import ExampleModel
from app.infrastructure.db.models.integrations.integrations import Integrations
from app.infrastructure.db.models.integrations.integrations_requests_details import RequestDetails
from app.infrastructure.db.models.integrations.auth_provider import AuthProvider
from app.infrastructure.db.models.logging.vans import LogPrePedidosVansModels
from app.infrastructure.db.models.logging.integrations import IntegrationLogs

# VANs
from app.infrastructure.db.models.vans.pre_pedidos import PrePedido, PrePedidoItem, PrePedidoFaturamento
from app.infrastructure.db.models.vans.pedidos import Pedido, PedidoItem, PedidoComplementoVans
from app.infrastructure.db.models.vans.notas_fiscais import NotaFiscal, NotaFiscalItem
from app.infrastructure.db.models.vans.configuracao import ProjetoSiglas, OrigemSistemas, ProjetoSiglaOrigem


__all__ = [
    "ExampleModel",
    "Integrations", "RequestDetails", "AuthProvider",
    "LogPrePedidosVansModels", "IntegrationLogs",
    "PrePedido", "PrePedidoItem", "PrePedidoFaturamento",
    "Pedido", "PedidoItem", "PedidoComplementoVans",
    "NotaFiscal", "NotaFiscalItem",
    "ProjetoSiglas", "OrigemSistemas", "ProjetoSiglaOrigem",
]
