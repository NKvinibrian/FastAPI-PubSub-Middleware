from typing import Protocol, Optional

from app.domain.entities.vans.pre_pedidos import (
    PrePedidoEntity,
    PrePedidoItemEntity,
    PrePedidoFaturamentoEntity,
)


class PrePedidoRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de PrePedido."""

    def get_all(self) -> list[PrePedidoEntity]:
        """Retorna todos os pré-pedidos."""
        ...

    def get_by_id(self, pre_pedido_id: int) -> Optional[PrePedidoEntity]:
        """Busca um pré-pedido pelo ID."""
        ...

    def get_by_origem_sistema_id(self, origem_sistema_id: str) -> Optional[PrePedidoEntity]:
        """Busca pré-pedido pelo ID no sistema de origem (VAN)."""
        ...

    def get_by_erp_confirmed_not_vans_confirmed(self) -> list[PrePedidoEntity]:
        """Retorna pré-pedidos confirmados no ERP mas não confirmados na VAN."""
        ...

    def get_by_order_cancellation_not_sent(self) -> list[PrePedidoEntity]:
        """Retorna pré-pedidos com cancelamento pendente de envio."""
        ...

    def create(self, pre_pedido: PrePedidoEntity) -> PrePedidoEntity:
        """Cria um novo pré-pedido."""
        ...

    def update(self, pre_pedido: PrePedidoEntity) -> PrePedidoEntity:
        """Atualiza um pré-pedido existente."""
        ...

    def delete(self, pre_pedido_id: int) -> None:
        """Remove um pré-pedido pelo ID (soft delete)."""
        ...


class PrePedidoItemRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de PrePedidoItem."""

    def get_all(self) -> list[PrePedidoItemEntity]:
        """Retorna todos os itens."""
        ...

    def get_by_id(self, item_id: int) -> Optional[PrePedidoItemEntity]:
        """Busca um item pelo ID."""
        ...

    def get_by_pre_pedido_id(self, pre_pedido_id: int) -> list[PrePedidoItemEntity]:
        """Retorna itens de um pré-pedido."""
        ...

    def create(self, item: PrePedidoItemEntity) -> PrePedidoItemEntity:
        """Cria um novo item."""
        ...

    def update(self, item: PrePedidoItemEntity) -> PrePedidoItemEntity:
        """Atualiza um item existente."""
        ...

    def delete(self, item_id: int) -> None:
        """Remove um item pelo ID."""
        ...


class PrePedidoFaturamentoRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de PrePedidoFaturamento."""

    def get_all(self) -> list[PrePedidoFaturamentoEntity]:
        """Retorna todos os faturamentos."""
        ...

    def get_by_id(self, faturamento_id: int) -> Optional[PrePedidoFaturamentoEntity]:
        """Busca um faturamento pelo ID."""
        ...

    def get_by_pre_pedido_id(self, pre_pedido_id: int) -> list[PrePedidoFaturamentoEntity]:
        """Retorna faturamentos de um pré-pedido."""
        ...

    def create(self, faturamento: PrePedidoFaturamentoEntity) -> PrePedidoFaturamentoEntity:
        """Cria um novo faturamento."""
        ...

    def update(self, faturamento: PrePedidoFaturamentoEntity) -> PrePedidoFaturamentoEntity:
        """Atualiza um faturamento existente."""
        ...

    def delete(self, faturamento_id: int) -> None:
        """Remove um faturamento pelo ID."""
        ...
