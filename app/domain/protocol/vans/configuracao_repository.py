from typing import Protocol, Optional

from app.domain.entities.vans.configuracao import (
    ProjetoSiglasEntity,
    OrigemSistemasEntity,
    ProjetoSiglaOrigemEntity,
)


class ProjetoSiglasRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de ProjetoSiglas."""

    def get_all(self) -> list[ProjetoSiglasEntity]:
        """Retorna todas as siglas de projeto."""
        ...

    def get_by_id(self, projeto_id: int) -> Optional[ProjetoSiglasEntity]:
        """Busca uma sigla pelo ID."""
        ...

    def get_by_sigla(self, projeto_sigla: str) -> Optional[ProjetoSiglasEntity]:
        """Busca pelo código da sigla (ex: SAN, RCH, LIB)."""
        ...

    def create(self, projeto: ProjetoSiglasEntity) -> ProjetoSiglasEntity:
        """Cria uma nova sigla de projeto."""
        ...

    def update(self, projeto: ProjetoSiglasEntity) -> ProjetoSiglasEntity:
        """Atualiza uma sigla existente."""
        ...

    def delete(self, projeto_id: int) -> None:
        """Remove uma sigla pelo ID (soft delete)."""
        ...


class OrigemSistemasRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de OrigemSistemas."""

    def get_all(self) -> list[OrigemSistemasEntity]:
        """Retorna todos os sistemas de origem."""
        ...

    def get_by_id(self, origem_id: int) -> Optional[OrigemSistemasEntity]:
        """Busca um sistema de origem pelo ID."""
        ...

    def get_by_origem_sistema(self, origem_sistema: str) -> Optional[OrigemSistemasEntity]:
        """Busca pelo nome do sistema (ex: Funcional)."""
        ...

    def create(self, origem: OrigemSistemasEntity) -> OrigemSistemasEntity:
        """Cria um novo sistema de origem."""
        ...

    def update(self, origem: OrigemSistemasEntity) -> OrigemSistemasEntity:
        """Atualiza um sistema existente."""
        ...

    def delete(self, origem_id: int) -> None:
        """Remove um sistema pelo ID (soft delete)."""
        ...


class ProjetoSiglaOrigemRepositoryProtocol(Protocol):
    """Protocolo para operações CRUD de ProjetoSiglaOrigem."""

    def get_all(self) -> list[ProjetoSiglaOrigemEntity]:
        """Retorna todos os vínculos projeto-origem."""
        ...

    def get_by_id(self, vinculo_id: int) -> Optional[ProjetoSiglaOrigemEntity]:
        """Busca um vínculo pelo ID."""
        ...

    def get_by_projeto_sigla_id(self, projeto_sigla_id: int) -> list[ProjetoSiglaOrigemEntity]:
        """Retorna vínculos de um projeto."""
        ...

    def get_by_origem_sistema_id(self, origem_sistema_id: int) -> list[ProjetoSiglaOrigemEntity]:
        """Retorna vínculos de um sistema de origem."""
        ...

    def create(self, vinculo: ProjetoSiglaOrigemEntity) -> ProjetoSiglaOrigemEntity:
        """Cria um novo vínculo."""
        ...

    def update(self, vinculo: ProjetoSiglaOrigemEntity) -> ProjetoSiglaOrigemEntity:
        """Atualiza um vínculo existente."""
        ...

    def delete(self, vinculo_id: int) -> None:
        """Remove um vínculo pelo ID (soft delete)."""
        ...