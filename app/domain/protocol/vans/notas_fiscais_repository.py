from typing import Protocol, Optional

from app.domain.entities.vans.notas_fiscais import NotaFiscalEntity, NotaFiscalItemEntity


class NotaFiscalRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de NotaFiscal."""

    def get_all(self) -> list[NotaFiscalEntity]:
        """Retorna todas as notas fiscais."""
        ...

    def get_by_id(self, nota_fiscal_id: int) -> Optional[NotaFiscalEntity]:
        """Busca uma nota fiscal pelo ID."""
        ...

    def get_by_pedido_id(self, pedido_id: int) -> list[NotaFiscalEntity]:
        """Retorna notas fiscais de um pedido."""
        ...

    def get_by_chave_acesso(self, chave_acesso: str) -> Optional[NotaFiscalEntity]:
        """Busca nota fiscal pela chave de acesso."""
        ...

    def create(self, nota_fiscal: NotaFiscalEntity) -> NotaFiscalEntity:
        """Cria uma nova nota fiscal."""
        ...

    def update(self, nota_fiscal: NotaFiscalEntity) -> NotaFiscalEntity:
        """Atualiza uma nota fiscal existente."""
        ...

    def delete(self, nota_fiscal_id: int) -> None:
        """Remove uma nota fiscal pelo ID (soft delete)."""
        ...


class NotaFiscalItemRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de NotaFiscalItem."""

    def get_all(self) -> list[NotaFiscalItemEntity]:
        """Retorna todos os itens."""
        ...

    def get_by_id(self, item_id: int) -> Optional[NotaFiscalItemEntity]:
        """Busca um item pelo ID."""
        ...

    def get_by_notafiscal_id(self, notafiscal_id: int) -> list[NotaFiscalItemEntity]:
        """Retorna itens de uma nota fiscal."""
        ...

    def create(self, item: NotaFiscalItemEntity) -> NotaFiscalItemEntity:
        """Cria um novo item."""
        ...

    def update(self, item: NotaFiscalItemEntity) -> NotaFiscalItemEntity:
        """Atualiza um item existente."""
        ...

    def delete(self, item_id: int) -> None:
        """Remove um item pelo ID."""
        ...