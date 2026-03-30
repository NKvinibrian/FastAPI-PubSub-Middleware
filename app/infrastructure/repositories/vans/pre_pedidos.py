"""
Repositórios de PrePedido, PrePedidoItem e PrePedidoFaturamento.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.vans.pre_pedidos import (
    PrePedidoEntity,
    PrePedidoItemEntity,
    PrePedidoFaturamentoEntity,
)
from app.infrastructure.db.models.vans.pre_pedidos import (
    PrePedido,
    PrePedidoItem,
    PrePedidoFaturamento,
)
from app.domain.protocol.vans.pre_pedidos_repository import (
    PrePedidoRepositoryProtocol,
    PrePedidoItemRepositoryProtocol,
    PrePedidoFaturamentoRepositoryProtocol,
)


# ═══════════════════════════════════════════════════════════════════════
#  PrePedidoRepository
# ═══════════════════════════════════════════════════════════════════════

class PrePedidoRepository(PrePedidoRepositoryProtocol):
    """Repositório para persistência de PrePedido no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: PrePedido) -> PrePedidoEntity:
        return PrePedidoEntity(
            id=m.id,
            origem_sistema_id=m.origem_sistema_id,
            origem_industria_pedido_id=m.origem_industria_pedido_id,
            origem_industria_codigo=m.origem_industria_codigo,
            tipo_pedido=m.tipo_pedido,
            origem_sistema=m.origem_sistema,
            origem_industria=m.origem_industria,
            origem_log_uuid=m.origem_log_uuid,
            origem_industria_created_at=m.origem_industria_created_at,
            informacoes_adicionais=m.informacoes_adicionais,
            observacao=m.observacao,
            status=m.status,
            distribuidor_cnpj=m.distribuidor_cnpj,
            prazo_negociado=m.prazo_negociado,
            condicao_comercial=m.condicao_comercial,
            margem=m.margem,
            pedido_bonificado=m.pedido_bonificado,
            entrega_programada=m.entrega_programada,
            tipo_origem=m.tipo_origem,
            distribuidor_filial_cnpj=m.distribuidor_filial_cnpj,
            distribuidor_matriz_cnpj=m.distribuidor_matriz_cnpj,
            vendedor_codigo=m.vendedor_codigo,
            nf_confirmed=m.nf_confirmed,
            tipo_faturamento=m.tipo_faturamento,
            cliente_codigo=m.cliente_codigo,
            cliente_email=m.cliente_email,
            cliente_tipo=m.cliente_tipo,
            cliente_nome_fantasia=m.cliente_nome_fantasia,
            cliente_razao_social=m.cliente_razao_social,
            cliente_telefone=m.cliente_telefone,
            cliente_inscricao_estadual=m.cliente_inscricao_estadual,
            cliente_cpf_cnpj=m.cliente_cpf_cnpj,
            entrega_rua=m.entrega_rua,
            entrega_numero=m.entrega_numero,
            entrega_bairro=m.entrega_bairro,
            entrega_complemento=m.entrega_complemento,
            entrega_observacao=m.entrega_observacao,
            entrega_cidade=m.entrega_cidade,
            entrega_estado=m.entrega_estado,
            entrega_cep=m.entrega_cep,
            destinatario_nome=m.destinatario_nome,
            destinario_cpf_cnpj=m.destinario_cpf_cnpj,
            entrega_status=m.entrega_status,
            erp_confirmed=m.erp_confirmed,
            vans_confirmed=m.vans_confirmed,
            delivery_at=m.delivery_at,
            delivered_at=m.delivered_at,
            fetched_at=m.fetched_at,
            erp_sended=m.erp_sended,
            erp_returned=m.erp_returned,
            motivo_atendimento=m.motivo_atendimento,
            message_id=m.message_id,
            order_cancellation_sent=m.order_cancellation_sent,
            central_processos_id=m.central_processos_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[PrePedidoEntity]:
        results = self._db.scalars(select(PrePedido)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, pre_pedido_id: int) -> Optional[PrePedidoEntity]:
        result = self._db.scalars(
            select(PrePedido).where(PrePedido.id == pre_pedido_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_origem_sistema_id(self, origem_sistema_id: str) -> Optional[PrePedidoEntity]:
        result = self._db.scalars(
            select(PrePedido).where(PrePedido.origem_sistema_id == origem_sistema_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_erp_confirmed_not_vans_confirmed(self) -> list[PrePedidoEntity]:
        results = self._db.scalars(
            select(PrePedido).where(
                PrePedido.erp_confirmed == True,
                PrePedido.vans_confirmed == False,
                PrePedido.status == True,
            )
        ).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_order_cancellation_not_sent(self) -> list[PrePedidoEntity]:
        results = self._db.scalars(
            select(PrePedido).where(
                PrePedido.order_cancellation_sent == False,
                PrePedido.status == False,
            )
        ).all()
        return [self._map_to_entity(r) for r in results]

    def create(self, pre_pedido: PrePedidoEntity) -> PrePedidoEntity:
        db_obj = PrePedido(
            origem_sistema_id=pre_pedido.origem_sistema_id,
            origem_industria_pedido_id=pre_pedido.origem_industria_pedido_id,
            origem_industria_codigo=pre_pedido.origem_industria_codigo,
            tipo_pedido=pre_pedido.tipo_pedido,
            origem_sistema=pre_pedido.origem_sistema,
            origem_industria=pre_pedido.origem_industria,
            origem_log_uuid=pre_pedido.origem_log_uuid,
            origem_industria_created_at=pre_pedido.origem_industria_created_at,
            informacoes_adicionais=pre_pedido.informacoes_adicionais,
            observacao=pre_pedido.observacao,
            distribuidor_cnpj=pre_pedido.distribuidor_cnpj,
            prazo_negociado=pre_pedido.prazo_negociado,
            condicao_comercial=pre_pedido.condicao_comercial,
            margem=pre_pedido.margem,
            pedido_bonificado=pre_pedido.pedido_bonificado,
            entrega_programada=pre_pedido.entrega_programada,
            tipo_origem=pre_pedido.tipo_origem,
            distribuidor_filial_cnpj=pre_pedido.distribuidor_filial_cnpj,
            distribuidor_matriz_cnpj=pre_pedido.distribuidor_matriz_cnpj,
            vendedor_codigo=pre_pedido.vendedor_codigo,
            cliente_codigo=pre_pedido.cliente_codigo,
            cliente_email=pre_pedido.cliente_email,
            cliente_tipo=pre_pedido.cliente_tipo,
            cliente_nome_fantasia=pre_pedido.cliente_nome_fantasia,
            cliente_razao_social=pre_pedido.cliente_razao_social,
            cliente_telefone=pre_pedido.cliente_telefone,
            cliente_inscricao_estadual=pre_pedido.cliente_inscricao_estadual,
            cliente_cpf_cnpj=pre_pedido.cliente_cpf_cnpj,
            erp_confirmed=pre_pedido.erp_confirmed,
            vans_confirmed=pre_pedido.vans_confirmed,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, pre_pedido: PrePedidoEntity) -> PrePedidoEntity:
        result = self._db.scalars(
            select(PrePedido).where(PrePedido.id == pre_pedido.id)
        ).first()
        if result is None:
            raise ValueError(f"PrePedido with id={pre_pedido.id} not found.")
        result.erp_confirmed = pre_pedido.erp_confirmed
        result.vans_confirmed = pre_pedido.vans_confirmed
        result.erp_sended = pre_pedido.erp_sended
        result.erp_returned = pre_pedido.erp_returned
        result.motivo_atendimento = pre_pedido.motivo_atendimento
        result.message_id = pre_pedido.message_id
        result.order_cancellation_sent = pre_pedido.order_cancellation_sent
        result.entrega_status = pre_pedido.entrega_status
        result.nf_confirmed = pre_pedido.nf_confirmed
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, pre_pedido_id: int) -> None:
        result = self._db.scalars(
            select(PrePedido).where(PrePedido.id == pre_pedido_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  PrePedidoItemRepository
# ═══════════════════════════════════════════════════════════════════════

class PrePedidoItemRepository(PrePedidoItemRepositoryProtocol):
    """Repositório para persistência de PrePedidoItem no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: PrePedidoItem) -> PrePedidoItemEntity:
        return PrePedidoItemEntity(
            id=m.id,
            pre_pedido_id=m.pre_pedido_id,
            ean=m.ean,
            valor_bruto=m.valor_bruto,
            quantidade=m.quantidade,
            desconto_percentual=m.desconto_percentual,
            desconto_valor=m.desconto_valor,
            valor_liquido=m.valor_liquido,
            produto_monitorado=m.produto_monitorado,
            observacao=m.observacao,
            prazo=m.prazo,
            motivo_atendimento=m.motivo_atendimento,
        )

    def get_all(self) -> list[PrePedidoItemEntity]:
        results = self._db.scalars(select(PrePedidoItem)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, item_id: int) -> Optional[PrePedidoItemEntity]:
        result = self._db.scalars(
            select(PrePedidoItem).where(PrePedidoItem.id == item_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_pre_pedido_id(self, pre_pedido_id: int) -> list[PrePedidoItemEntity]:
        results = self._db.scalars(
            select(PrePedidoItem).where(PrePedidoItem.pre_pedido_id == pre_pedido_id)
        ).all()
        return [self._map_to_entity(r) for r in results]

    def create(self, item: PrePedidoItemEntity) -> PrePedidoItemEntity:
        db_obj = PrePedidoItem(
            pre_pedido_id=item.pre_pedido_id,
            ean=item.ean,
            valor_bruto=item.valor_bruto,
            quantidade=item.quantidade,
            desconto_percentual=item.desconto_percentual,
            desconto_valor=item.desconto_valor,
            valor_liquido=item.valor_liquido,
            produto_monitorado=item.produto_monitorado,
            observacao=item.observacao,
            prazo=item.prazo,
            motivo_atendimento=item.motivo_atendimento,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, item: PrePedidoItemEntity) -> PrePedidoItemEntity:
        result = self._db.scalars(
            select(PrePedidoItem).where(PrePedidoItem.id == item.id)
        ).first()
        if result is None:
            raise ValueError(f"PrePedidoItem with id={item.id} not found.")
        result.ean = item.ean
        result.valor_bruto = item.valor_bruto
        result.quantidade = item.quantidade
        result.desconto_percentual = item.desconto_percentual
        result.desconto_valor = item.desconto_valor
        result.valor_liquido = item.valor_liquido
        result.produto_monitorado = item.produto_monitorado
        result.observacao = item.observacao
        result.prazo = item.prazo
        result.motivo_atendimento = item.motivo_atendimento
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, item_id: int) -> None:
        result = self._db.scalars(
            select(PrePedidoItem).where(PrePedidoItem.id == item_id)
        ).first()
        if result is not None:
            self._db.delete(result)
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  PrePedidoFaturamentoRepository
# ═══════════════════════════════════════════════════════════════════════

class PrePedidoFaturamentoRepository(PrePedidoFaturamentoRepositoryProtocol):
    """Repositório para persistência de PrePedidoFaturamento no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: PrePedidoFaturamento) -> PrePedidoFaturamentoEntity:
        return PrePedidoFaturamentoEntity(
            id=m.id,
            pre_pedido_id=m.pre_pedido_id,
            tipo_pagamento_id=m.tipo_pagamento_id,
            tipo_pagamento=m.tipo_pagamento,
            prazo_pagamento_id=m.prazo_pagamento_id,
            prazo_pagamento=m.prazo_pagamento,
            numero_dias_prazo=m.numero_dias_prazo,
            pedido_num_bonificacao=m.pedido_num_bonificacao,
        )

    def get_all(self) -> list[PrePedidoFaturamentoEntity]:
        results = self._db.scalars(select(PrePedidoFaturamento)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, faturamento_id: int) -> Optional[PrePedidoFaturamentoEntity]:
        result = self._db.scalars(
            select(PrePedidoFaturamento).where(PrePedidoFaturamento.id == faturamento_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_pre_pedido_id(self, pre_pedido_id: int) -> list[PrePedidoFaturamentoEntity]:
        results = self._db.scalars(
            select(PrePedidoFaturamento).where(
                PrePedidoFaturamento.pre_pedido_id == pre_pedido_id
            )
        ).all()
        return [self._map_to_entity(r) for r in results]

    def create(self, faturamento: PrePedidoFaturamentoEntity) -> PrePedidoFaturamentoEntity:
        db_obj = PrePedidoFaturamento(
            pre_pedido_id=faturamento.pre_pedido_id,
            tipo_pagamento_id=faturamento.tipo_pagamento_id,
            tipo_pagamento=faturamento.tipo_pagamento,
            prazo_pagamento_id=faturamento.prazo_pagamento_id,
            prazo_pagamento=faturamento.prazo_pagamento,
            numero_dias_prazo=faturamento.numero_dias_prazo,
            pedido_num_bonificacao=faturamento.pedido_num_bonificacao,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, faturamento: PrePedidoFaturamentoEntity) -> PrePedidoFaturamentoEntity:
        result = self._db.scalars(
            select(PrePedidoFaturamento).where(PrePedidoFaturamento.id == faturamento.id)
        ).first()
        if result is None:
            raise ValueError(f"PrePedidoFaturamento with id={faturamento.id} not found.")
        result.tipo_pagamento_id = faturamento.tipo_pagamento_id
        result.tipo_pagamento = faturamento.tipo_pagamento
        result.prazo_pagamento_id = faturamento.prazo_pagamento_id
        result.prazo_pagamento = faturamento.prazo_pagamento
        result.numero_dias_prazo = faturamento.numero_dias_prazo
        result.pedido_num_bonificacao = faturamento.pedido_num_bonificacao
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, faturamento_id: int) -> None:
        result = self._db.scalars(
            select(PrePedidoFaturamento).where(PrePedidoFaturamento.id == faturamento_id)
        ).first()
        if result is not None:
            self._db.delete(result)
            self._db.commit()