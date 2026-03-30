from typing import Protocol, Optional

from app.domain.entities.vans.pedidos import (
    PedidoEntity,
    PedidoItemEntity,
    PedidoComplementoVansEntity,
)


class PedidoRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de Pedido (Datasul)."""

    def get_all(self) -> list[PedidoEntity]:
        """Retorna todos os pedidos."""
        ...

    def get_by_id(self, pedido_id: int) -> Optional[PedidoEntity]:
        """Busca um pedido pelo ID."""
        ...

    def get_by_id_pedido_datasul(self, id_pedido_datasul: int) -> Optional[PedidoEntity]:
        """Busca pedido pelo ID do Datasul."""
        ...

    def create(self, pedido: PedidoEntity) -> PedidoEntity:
        """Cria um novo pedido."""
        ...

    def update(self, pedido: PedidoEntity) -> PedidoEntity:
        """Atualiza um pedido existente."""
        ...

    def delete(self, pedido_id: int) -> None:
        """Remove um pedido pelo ID (soft delete)."""
        ...


class PedidoItemRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de PedidoItem."""

    def get_all(self) -> list[PedidoItemEntity]:
        """Retorna todos os itens."""
        ...

    def get_by_id(self, item_id: int) -> Optional[PedidoItemEntity]:
        """Busca um item pelo ID."""
        ...

    def get_by_pedido_id(self, pedido_id: int) -> list[PedidoItemEntity]:
        """Retorna itens de um pedido."""
        ...

    def create(self, item: PedidoItemEntity) -> PedidoItemEntity:
        """Cria um novo item."""
        ...

    def update(self, item: PedidoItemEntity) -> PedidoItemEntity:
        """Atualiza um item existente."""
        ...

    def delete(self, item_id: int) -> None:
        """Remove um item pelo ID."""
        ...


class PedidoComplementoVansRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de PedidoComplementoVans."""

    def get_all(self) -> list[PedidoComplementoVansEntity]:
        """Retorna todos os complementos."""
        ...

    def get_by_id(self, complemento_id: int) -> Optional[PedidoComplementoVansEntity]:
        """Busca um complemento pelo ID."""
        ...

    def get_by_id_pedido_datasul(self, id_pedido_datasul: int) -> list[PedidoComplementoVansEntity]:
        """Retorna complementos de um pedido Datasul."""
        ...

    def get_by_id_pedido_vans(self, id_pedido_vans: str) -> Optional[PedidoComplementoVansEntity]:
        """Busca complemento pelo ID do pedido na VAN."""
        ...

    def create(self, complemento: PedidoComplementoVansEntity) -> PedidoComplementoVansEntity:
        """Cria um novo complemento."""
        ...

    def update(self, complemento: PedidoComplementoVansEntity) -> PedidoComplementoVansEntity:
        """Atualiza um complemento existente."""
        ...

    def delete(self, complemento_id: int) -> None:
        """Remove um complemento pelo ID (soft delete)."""
        ...
