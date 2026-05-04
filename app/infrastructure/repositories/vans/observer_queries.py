"""
Repositório de queries cross-table para o Observer.

Adaptado do ObserverBase (tmp/app/vans/observer/base/observer.py) para a
nova estrutura que usa PedidoComplementoVans como tabela ponte entre
PrePedido e Pedido.

Join path antigo:  PrePedido.id == Pedido.pedido_num
Join path novo:    PrePedido.origem_sistema_id == PedidoComplementoVans.id_pedido_vans
                   AND PedidoComplementoVans.origem_van == origin_system
                   AND PedidoComplementoVans.id_pedido_datasul == Pedido.id_pedido_datasul
"""

import logging
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.entities.vans.notas_fiscais import NotaFiscalEntity, NotaFiscalItemEntity
from app.domain.entities.vans.pedidos import PedidoEntity, PedidoItemEntity
from app.domain.entities.vans.pre_pedidos import PrePedidoEntity, PrePedidoItemEntity
from app.infrastructure.db.models.vans.notas_fiscais import NotaFiscal, NotaFiscalItem
from app.infrastructure.db.models.vans.pedidos import (
    Pedido,
    PedidoComplementoVans,
    PedidoItem,
)
from app.infrastructure.db.models.vans.pre_pedidos import PrePedido, PrePedidoItem

# Reutiliza mappers estáticos dos repositórios existentes
from app.infrastructure.repositories.vans.notas_fiscais import (
    NotaFiscalItemRepository,
    NotaFiscalRepository,
)
from app.infrastructure.repositories.vans.pedidos import (
    PedidoItemRepository,
    PedidoRepository,
)
from app.infrastructure.repositories.vans.pre_pedidos import (
    PrePedidoItemRepository,
    PrePedidoRepository,
)

logger = logging.getLogger(__name__)

# Etapas do Datasul usadas nos filtros (espelha o ObserverBase antigo)
_ETAPAS_APROVADO = ["Pedido Efetivado", "Pedido Aprovado Crédito"]
_ETAPAS_CANCELADO = ["Pedido Cancelado"]


class ObserverQueryRepository:
    """
    Queries cross-table para os fluxos do Observer.

    Cada método encapsula os JOINs entre pre_pedidos,
    pedidos_complemento_vans, pedidos e notas_fiscais.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ═══════════════════════════════════════════════════════════════════
    #  Helpers de JOIN
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _complemento_join():
        """Condição de JOIN: PrePedido → PedidoComplementoVans."""
        return and_(
            PedidoComplementoVans.id_pedido_vans == PrePedido.origem_sistema_id,
            PedidoComplementoVans.origem_van == PrePedido.origem_sistema,
        )

    @staticmethod
    def _pedido_join():
        """Condição de JOIN: PedidoComplementoVans → Pedido."""
        return Pedido.id_pedido_datasul == PedidoComplementoVans.id_pedido_datasul

    def _fetch_pre_pedidos_by_ids(self, ids: list[int]) -> list[PrePedidoEntity]:
        """Busca PrePedidoEntities a partir de uma lista de IDs."""
        if not ids:
            return []
        results = self._db.scalars(
            select(PrePedido).where(PrePedido.id.in_(ids))
        ).all()
        return [PrePedidoRepository._map_to_entity(r) for r in results]

    # ═══════════════════════════════════════════════════════════════════
    #  1. ORDER_RETURN — pedidos aprovados pendentes de retorno
    # ═══════════════════════════════════════════════════════════════════

    def get_pre_pedidos_for_order_return(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Adaptado de ObserverBase.get_orders_ids_with_filters().

        JOIN: PrePedido → ComplementoVans → Pedido
        WHERE: descricao_etapa IN (Aprovado/Efetivado), vans_confirmed IS NOT True
        """
        stmt = (
            select(PrePedido.id)
            .select_from(PrePedido)
            .join(PedidoComplementoVans, self._complemento_join())
            .join(Pedido, self._pedido_join())
            .where(
                PrePedido.origem_sistema == origin_system,
                Pedido.descricao_etapa.in_(_ETAPAS_APROVADO),
                PrePedido.vans_confirmed.is_not(True),
            )
            .distinct()
        )
        ids = [row[0] for row in self._db.execute(stmt).all()]
        return self._fetch_pre_pedidos_by_ids(ids)

    # ═══════════════════════════════════════════════════════════════════
    #  2. ORDER_RETURN_REJECTION — pedidos cancelados pendentes de rejeição
    # ═══════════════════════════════════════════════════════════════════

    def get_pre_pedidos_for_rejection(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Adaptado de ObserverBase.get_cancelled_orders_ids_with_filters().

        JOIN: PrePedido → ComplementoVans → Pedido
        WHERE: descricao_etapa IN (Cancelado), vans_confirmed IS NOT True
        """
        stmt = (
            select(PrePedido.id)
            .select_from(PrePedido)
            .join(PedidoComplementoVans, self._complemento_join())
            .join(Pedido, self._pedido_join())
            .where(
                PrePedido.origem_sistema == origin_system,
                Pedido.descricao_etapa.in_(_ETAPAS_CANCELADO),
                PrePedido.order_cancellation_sent.is_not(True),
                PrePedido.vans_confirmed.is_not(True),
            )
            .distinct()
        )
        ids = [row[0] for row in self._db.execute(stmt).all()]
        return self._fetch_pre_pedidos_by_ids(ids)

    # ═══════════════════════════════════════════════════════════════════
    #  3. RETURN_CANCELLATION — já retornados mas cancelados depois
    # ═══════════════════════════════════════════════════════════════════

    def get_pre_pedidos_for_cancellation(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Adaptado de ObserverBase.get_just_cancelled_orders_ids_with_filters().

        JOIN: PrePedido → ComplementoVans → Pedido
        WHERE: descricao_etapa IN (Cancelado), vans_confirmed IS True (já retornado)
        """
        stmt = (
            select(PrePedido.id)
            .select_from(PrePedido)
            .join(PedidoComplementoVans, self._complemento_join())
            .join(Pedido, self._pedido_join())
            .where(
                PrePedido.origem_sistema == origin_system,
                Pedido.descricao_etapa.in_(_ETAPAS_CANCELADO),
                PrePedido.order_cancellation_sent.is_not(True),
                PrePedido.vans_confirmed.is_(True),
            )
            .distinct()
        )
        ids = [row[0] for row in self._db.execute(stmt).all()]
        return self._fetch_pre_pedidos_by_ids(ids)

    # ═══════════════════════════════════════════════════════════════════
    #  4. RETURN_INVOICES — NFs pendentes de retorno
    # ═══════════════════════════════════════════════════════════════════

    def get_pre_pedidos_for_invoice(self, origin_system: str) -> list[PrePedidoEntity]:
        """
        Adaptado de ObserverBase.get_invoices_ids_with_filters().

        JOIN: PrePedido → ComplementoVans → Pedido
        WHERE: descricao_etapa IN (Aprovado/Efetivado), nf_confirmed IS NOT True
        """
        stmt = (
            select(PrePedido.id)
            .select_from(PrePedido)
            .join(PedidoComplementoVans, self._complemento_join())
            .join(Pedido, self._pedido_join())
            .where(
                PrePedido.origem_sistema == origin_system,
                Pedido.descricao_etapa.in_(_ETAPAS_APROVADO),
                PrePedido.nf_confirmed.is_not(True),
            )
            .distinct()
        )
        ids = [row[0] for row in self._db.execute(stmt).all()]
        return self._fetch_pre_pedidos_by_ids(ids)

    # ═══════════════════════════════════════════════════════════════════
    #  Lookups de dados relacionados
    # ═══════════════════════════════════════════════════════════════════

    def get_pedido_data(
        self, origem_sistema_id: str, origin_system: str,
    ) -> tuple[Optional[PedidoEntity], list[PedidoItemEntity]]:
        """
        Busca Pedido Datasul e seus itens vinculados ao pré-pedido.

        Caminho: origem_sistema_id → PedidoComplementoVans → Pedido → PedidoItem
        """
        complemento = self._db.scalars(
            select(PedidoComplementoVans).where(
                PedidoComplementoVans.id_pedido_vans == str(origem_sistema_id),
                PedidoComplementoVans.origem_van == origin_system,
            )
        ).first()

        if not complemento:
            return None, []

        pedido = self._db.scalars(
            select(Pedido).where(
                Pedido.id_pedido_datasul == complemento.id_pedido_datasul,
            )
        ).first()

        if not pedido:
            return None, []

        pedido_itens = list(
            self._db.scalars(
                select(PedidoItem).where(PedidoItem.pedido_id == pedido.id)
            ).all()
        )

        return (
            PedidoRepository._map_to_entity(pedido),
            [PedidoItemRepository._map_to_entity(i) for i in pedido_itens],
        )

    def get_pre_pedido_itens(self, pre_pedido_id: int) -> list[PrePedidoItemEntity]:
        """Retorna itens de um pré-pedido."""
        results = self._db.scalars(
            select(PrePedidoItem).where(PrePedidoItem.pre_pedido_id == pre_pedido_id)
        ).all()
        return [PrePedidoItemRepository._map_to_entity(r) for r in results]

    def get_notas_fiscais_for_pre_pedido(
        self, origem_sistema_id: str, origin_system: str,
    ) -> list[NotaFiscalEntity]:
        """
        Busca NFs ativas vinculadas a um pré-pedido via complemento → pedido.
        """
        complemento = self._db.scalars(
            select(PedidoComplementoVans).where(
                PedidoComplementoVans.id_pedido_vans == str(origem_sistema_id),
                PedidoComplementoVans.origem_van == origin_system,
            )
        ).first()

        if not complemento:
            return []

        pedido = self._db.scalars(
            select(Pedido).where(
                Pedido.id_pedido_datasul == complemento.id_pedido_datasul,
            )
        ).first()

        if not pedido:
            return []

        notas = self._db.scalars(
            select(NotaFiscal).where(
                NotaFiscal.pedido_id == pedido.id,
                NotaFiscal.status == True,
            )
        ).all()

        return [NotaFiscalRepository._map_to_entity(nf) for nf in notas]

    def get_nota_fiscal_itens(self, notafiscal_id: int) -> list[NotaFiscalItemEntity]:
        """Retorna itens de uma nota fiscal."""
        results = self._db.scalars(
            select(NotaFiscalItem).where(NotaFiscalItem.notafiscal_id == notafiscal_id)
        ).all()
        return [NotaFiscalItemRepository._map_to_entity(r) for r in results]
