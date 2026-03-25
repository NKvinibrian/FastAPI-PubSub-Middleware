"""
Protocolo genérico para Parsers de pedido de VAN.

Define o contrato que todo parser de VAN deve implementar.
O parser é responsável apenas por converter dados brutos
no formato padronizado PrePedidoSchema.
"""

from typing import Protocol, Any

from app.api.v1.schemas.vans.pre_pedido import PrePedidoSchema


class OrderParserProtocol(Protocol):
    """
    Contrato genérico para parsers de pedido de VAN.

    Recebe lista de dicts brutos (vindos do fetcher) e retorna
    lista de PrePedidoSchema — um item por pedido.

    Parsers específicos de cada VAN devem implementar este protocolo,
    sobrescrevendo `_map_order()` para adaptar o mapeamento de campos.
    """

    def parse(self, raw_orders: list[dict[str, Any]]) -> list[PrePedidoSchema]:
        """
        Converte pedidos brutos em lista de PrePedidoSchema.

        Args:
            raw_orders: Lista de dicts vindos diretamente do fetcher.

        Returns:
            Lista de PrePedidoSchema (um por pedido válido).
        """
        ...

