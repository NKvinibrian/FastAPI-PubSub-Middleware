"""
Protocolo para queries do Observer.

Define a interface de consultas cross-table necessárias para
os fluxos do Observer (retorno de pedidos, rejeição, NF, cancelamento).

Adaptado do ObserverBase do sistema legado para a nova estrutura
que usa PedidoComplementoVans como tabela ponte.
"""

from typing import Optional, Protocol

from app.domain.entities.vans.notas_fiscais import NotaFiscalEntity, NotaFiscalItemEntity
from app.domain.entities.vans.pedidos import PedidoEntity, PedidoItemEntity
from app.domain.entities.vans.pre_pedidos import PrePedidoEntity, PrePedidoItemEntity


class ObserverQueryRepositoryProtocol(Protocol):
    """
    Consultas cross-table para os fluxos do Observer.

    Cada método encapsula JOINs entre pre_pedidos, pedidos_complemento_vans,
    pedidos e notas_fiscais, filtrando por origem (VAN) e descricao_etapa.
    """

    def get_pre_pedidos_for_order_return(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Pre-pedidos pendentes de retorno à VAN (ORDER_RETURN).

        Critérios (adaptados do ObserverBase.get_orders_ids_with_filters):
            - PrePedido.origem_sistema == origin_system
            - Pedido.descricao_etapa IN ('Pedido Efetivado', 'Pedido Aprovado Crédito')
            - PrePedido.vans_confirmed IS NOT True
        """
        ...

    def get_pre_pedidos_for_rejection(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Pre-pedidos pendentes de retorno de rejeição (ORDER_RETURN_REJECTION).

        Critérios (adaptados do ObserverBase.get_cancelled_orders_ids_with_filters):
            - PrePedido.origem_sistema == origin_system
            - Pedido.descricao_etapa IN ('Pedido Cancelado')
            - PrePedido.vans_confirmed IS NOT True
            - PrePedido.order_cancellation_sent IS NOT True
        """
        ...

    def get_pre_pedidos_for_cancellation(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Pre-pedidos já retornados mas cancelados depois (RETURN_CANCELLATION).

        Critérios (adaptados do ObserverBase.get_just_cancelled_orders_ids_with_filters):
            - PrePedido.origem_sistema == origin_system
            - Pedido.descricao_etapa IN ('Pedido Cancelado')
            - PrePedido.vans_confirmed IS True (já retornado)
            - PrePedido.order_cancellation_sent IS NOT True
        """
        ...

    def get_pre_pedidos_for_invoice(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Pre-pedidos pendentes de retorno de NF (RETURN_INVOICES).

        Critérios (adaptados do ObserverBase.get_invoices_ids_with_filters):
            - PrePedido.origem_sistema == origin_system
            - Pedido.descricao_etapa IN ('Pedido Efetivado', 'Pedido Aprovado Crédito')
            - PrePedido.nf_confirmed IS NOT True
        """
        ...

    def get_pedido_data(
        self, origem_sistema_id: str, origin_system: str,
    ) -> tuple[Optional[PedidoEntity], list[PedidoItemEntity]]:
        """
        Busca Pedido Datasul e seus itens vinculados ao pré-pedido.

        Caminho: origem_sistema_id -> PedidoComplementoVans -> Pedido -> PedidoItem
        """
        ...

    def get_pre_pedido_itens(self, pre_pedido_id: int) -> list[PrePedidoItemEntity]:
        """Retorna itens de um pré-pedido."""
        ...

    def get_notas_fiscais_for_pre_pedido(
        self, origem_sistema_id: str, origin_system: str,
    ) -> list[NotaFiscalEntity]:
        """
        Busca NFs ativas vinculadas a um pré-pedido via complemento -> pedido.
        """
        ...

    def get_nota_fiscal_itens(self, notafiscal_id: int) -> list[NotaFiscalItemEntity]:
        """Retorna itens de uma nota fiscal."""
        ...
