"""
Repositórios de Pedido, PedidoItem e PedidoComplementoVans.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.vans.pedidos import (
    PedidoEntity,
    PedidoItemEntity,
    PedidoComplementoVansEntity,
)
from app.infrastructure.db.models.vans.pedidos import (
    Pedido,
    PedidoItem,
    PedidoComplementoVans,
)
from app.domain.protocol.vans.pedidos_repository import (
    PedidoRepositoryProtocol,
    PedidoItemRepositoryProtocol,
    PedidoComplementoVansRepositoryProtocol,
)


# ═══════════════════════════════════════════════════════════════════════
#  PedidoRepository
# ═══════════════════════════════════════════════════════════════════════

class PedidoRepository(PedidoRepositoryProtocol):
    """Repositório para persistência de Pedido no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: Pedido) -> PedidoEntity:
        return PedidoEntity(
            id=m.id,
            id_pedido_datasul=m.id_pedido_datasul,
            origem=m.origem,
            filial_cnpj=m.filial_cnpj,
            filial_id=m.filial_id,
            data_emissao=m.data_emissao,
            pedido_tipo=m.pedido_tipo,
            condicao_pagamento=m.condicao_pagamento,
            obs=m.obs,
            pedido_num=m.pedido_num,
            valor_pedido=m.valor_pedido,
            percentual_desconto=m.percentual_desconto,
            valor_desconto=m.valor_desconto,
            valor_bruto=m.valor_bruto,
            cliente_id=m.cliente_id,
            entidade_tipo=m.entidade_tipo,
            base_origem=m.base_origem,
            pedido_info=m.pedido_info,
            codigo_etapa=m.codigo_etapa,
            descricao_etapa=m.descricao_etapa,
            data_etapa=m.data_etapa,
            ordem_compra_id=m.ordem_compra_id,
            motivo_cancelamento=m.motivo_cancelamento,
            data_shelf_life=m.data_shelf_life,
            estoque_tipo=m.estoque_tipo,
            motivo_atendimento=m.motivo_atendimento,
            cnpj_transportadora=m.cnpj_transportadora,
            nome_transportadora=m.nome_transportadora,
            is_pbm=m.is_pbm,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[PedidoEntity]:
        results = self._db.scalars(select(Pedido)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, pedido_id: int) -> Optional[PedidoEntity]:
        result = self._db.scalars(
            select(Pedido).where(Pedido.id == pedido_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_id_pedido_datasul(self, id_pedido_datasul: int) -> Optional[PedidoEntity]:
        result = self._db.scalars(
            select(Pedido).where(Pedido.id_pedido_datasul == id_pedido_datasul)
        ).first()
        return self._map_to_entity(result) if result else None

    def create(self, pedido: PedidoEntity) -> PedidoEntity:
        db_obj = Pedido(
            id_pedido_datasul=pedido.id_pedido_datasul,
            origem=pedido.origem,
            filial_cnpj=pedido.filial_cnpj,
            filial_id=pedido.filial_id,
            data_emissao=pedido.data_emissao,
            pedido_tipo=pedido.pedido_tipo,
            condicao_pagamento=pedido.condicao_pagamento,
            obs=pedido.obs,
            pedido_num=pedido.pedido_num,
            valor_pedido=pedido.valor_pedido,
            percentual_desconto=pedido.percentual_desconto,
            valor_desconto=pedido.valor_desconto,
            valor_bruto=pedido.valor_bruto,
            cliente_id=pedido.cliente_id,
            entidade_tipo=pedido.entidade_tipo,
            base_origem=pedido.base_origem,
            pedido_info=pedido.pedido_info,
            codigo_etapa=pedido.codigo_etapa,
            descricao_etapa=pedido.descricao_etapa,
            motivo_atendimento=pedido.motivo_atendimento,
            cnpj_transportadora=pedido.cnpj_transportadora,
            nome_transportadora=pedido.nome_transportadora,
            is_pbm=pedido.is_pbm,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, pedido: PedidoEntity) -> PedidoEntity:
        result = self._db.scalars(
            select(Pedido).where(Pedido.id == pedido.id)
        ).first()
        if result is None:
            raise ValueError(f"Pedido with id={pedido.id} not found.")
        result.codigo_etapa = pedido.codigo_etapa
        result.descricao_etapa = pedido.descricao_etapa
        result.data_etapa = pedido.data_etapa
        result.motivo_cancelamento = pedido.motivo_cancelamento
        result.motivo_atendimento = pedido.motivo_atendimento
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, pedido_id: int) -> None:
        result = self._db.scalars(
            select(Pedido).where(Pedido.id == pedido_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  PedidoItemRepository
# ═══════════════════════════════════════════════════════════════════════

class PedidoItemRepository(PedidoItemRepositoryProtocol):
    """Repositório para persistência de PedidoItem no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: PedidoItem) -> PedidoItemEntity:
        return PedidoItemEntity(
            id=m.id,
            id_pedido_datasul=m.id_pedido_datasul,
            sequencia_id=m.sequencia_id,
            pedido_id=m.pedido_id,
            produto_id=m.produto_id,
            lote_id=m.lote_id,
            lote=m.lote,
            lote_cdi=m.lote_cdi,
            lote_quantidade_saida=m.lote_quantidade_saida,
            documento_num=m.documento_num,
            numero_fornecedor=m.numero_fornecedor,
            data_validade=m.data_validade,
            data_fabricacao=m.data_fabricacao,
            quantidade_original=m.quantidade_original,
            quantidade=m.quantidade,
            quantidade_convertida=m.quantidade_convertida,
            quantidade_faturar=m.quantidade_faturar,
            quantidade_reservada=m.quantidade_reservada,
            tipo_embalagem=m.tipo_embalagem,
            valor_unitario=m.valor_unitario,
            percentual_desconto=m.percentual_desconto,
            valor_desconto=m.valor_desconto,
            valor_bruto=m.valor_bruto,
            valor_total_liquido=m.valor_total_liquido,
            valor_total_bruto=m.valor_total_bruto,
            valor_total_desconto=m.valor_total_desconto,
            observacao=m.observacao,
            data_alteracao=m.data_alteracao,
            valor_frete=m.valor_frete,
            data_entrega=m.data_entrega,
            data_shelf_life=m.data_shelf_life,
            motivo_atendimento=m.motivo_atendimento,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[PedidoItemEntity]:
        results = self._db.scalars(select(PedidoItem)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, item_id: int) -> Optional[PedidoItemEntity]:
        result = self._db.scalars(
            select(PedidoItem).where(PedidoItem.id == item_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_pedido_id(self, pedido_id: int) -> list[PedidoItemEntity]:
        results = self._db.scalars(
            select(PedidoItem).where(PedidoItem.pedido_id == pedido_id)
        ).all()
        return [self._map_to_entity(r) for r in results]

    def create(self, item: PedidoItemEntity) -> PedidoItemEntity:
        db_obj = PedidoItem(
            id_pedido_datasul=item.id_pedido_datasul,
            sequencia_id=item.sequencia_id,
            pedido_id=item.pedido_id,
            produto_id=item.produto_id,
            quantidade=item.quantidade,
            valor_unitario=item.valor_unitario,
            percentual_desconto=item.percentual_desconto,
            valor_desconto=item.valor_desconto,
            valor_bruto=item.valor_bruto,
            valor_total_liquido=item.valor_total_liquido,
            valor_total_bruto=item.valor_total_bruto,
            observacao=item.observacao,
            motivo_atendimento=item.motivo_atendimento,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, item: PedidoItemEntity) -> PedidoItemEntity:
        result = self._db.scalars(
            select(PedidoItem).where(PedidoItem.id == item.id)
        ).first()
        if result is None:
            raise ValueError(f"PedidoItem with id={item.id} not found.")
        result.quantidade = item.quantidade
        result.valor_unitario = item.valor_unitario
        result.percentual_desconto = item.percentual_desconto
        result.valor_desconto = item.valor_desconto
        result.motivo_atendimento = item.motivo_atendimento
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, item_id: int) -> None:
        result = self._db.scalars(
            select(PedidoItem).where(PedidoItem.id == item_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  PedidoComplementoVansRepository
# ═══════════════════════════════════════════════════════════════════════

class PedidoComplementoVansRepository(PedidoComplementoVansRepositoryProtocol):
    """Repositório para persistência de PedidoComplementoVans no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: PedidoComplementoVans) -> PedidoComplementoVansEntity:
        return PedidoComplementoVansEntity(
            id=m.id,
            id_pedido_datasul=m.id_pedido_datasul,
            id_pedido_vans=m.id_pedido_vans,
            extra_data=m.extra_data,
            origem_van=m.origem_van,
            status_atual=m.status_atual,
            status_atual_van=m.status_atual_van,
            is_finished=m.is_finished,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[PedidoComplementoVansEntity]:
        results = self._db.scalars(select(PedidoComplementoVans)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, complemento_id: int) -> Optional[PedidoComplementoVansEntity]:
        result = self._db.scalars(
            select(PedidoComplementoVans).where(PedidoComplementoVans.id == complemento_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_id_pedido_datasul(self, id_pedido_datasul: int) -> list[PedidoComplementoVansEntity]:
        results = self._db.scalars(
            select(PedidoComplementoVans).where(
                PedidoComplementoVans.id_pedido_datasul == id_pedido_datasul
            )
        ).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id_pedido_vans(self, id_pedido_vans: str) -> Optional[PedidoComplementoVansEntity]:
        result = self._db.scalars(
            select(PedidoComplementoVans).where(
                PedidoComplementoVans.id_pedido_vans == id_pedido_vans
            )
        ).first()
        return self._map_to_entity(result) if result else None

    def create(self, complemento: PedidoComplementoVansEntity) -> PedidoComplementoVansEntity:
        db_obj = PedidoComplementoVans(
            id_pedido_datasul=complemento.id_pedido_datasul,
            id_pedido_vans=complemento.id_pedido_vans,
            extra_data=complemento.extra_data,
            origem_van=complemento.origem_van,
            status_atual=complemento.status_atual,
            status_atual_van=complemento.status_atual_van,
            is_finished=complemento.is_finished,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, complemento: PedidoComplementoVansEntity) -> PedidoComplementoVansEntity:
        result = self._db.scalars(
            select(PedidoComplementoVans).where(PedidoComplementoVans.id == complemento.id)
        ).first()
        if result is None:
            raise ValueError(f"PedidoComplementoVans with id={complemento.id} not found.")
        result.status_atual = complemento.status_atual
        result.status_atual_van = complemento.status_atual_van
        result.is_finished = complemento.is_finished
        result.extra_data = complemento.extra_data
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, complemento_id: int) -> None:
        result = self._db.scalars(
            select(PedidoComplementoVans).where(PedidoComplementoVans.id == complemento_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()
