"""
Repositórios de NotaFiscal e NotaFiscalItem.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.vans.notas_fiscais import NotaFiscalEntity, NotaFiscalItemEntity
from app.infrastructure.db.models.vans.notas_fiscais import NotaFiscal, NotaFiscalItem
from app.domain.protocol.vans.notas_fiscais_repository import (
    NotaFiscalRepositoryProtocol,
    NotaFiscalItemRepositoryProtocol,
)


# ═══════════════════════════════════════════════════════════════════════
#  NotaFiscalRepository
# ═══════════════════════════════════════════════════════════════════════

class NotaFiscalRepository(NotaFiscalRepositoryProtocol):
    """Repositório para persistência de NotaFiscal no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: NotaFiscal) -> NotaFiscalEntity:
        return NotaFiscalEntity(
            id=m.id,
            nota_id=m.nota_id,
            chave_acesso=m.chave_acesso,
            versao=m.versao,
            especie=m.especie,
            modelo=m.modelo,
            numero=m.numero,
            serie=m.serie,
            data_emissao=m.data_emissao,
            data_entrega=m.data_entrega,
            pedido_id=m.pedido_id,
            tipo_pedido=m.tipo_pedido,
            tipo_nota=m.tipo_nota,
            situacao=m.situacao,
            emitente_cnpj=m.emitente_cnpj,
            destinatario_cnpj=m.destinatario_cnpj,
            destinatario_nome=m.destinatario_nome,
            destinatario_logradouro=m.destinatario_logradouro,
            destinatario_numero=m.destinatario_numero,
            destinatario_complemento=m.destinatario_complemento,
            destinatario_bairro=m.destinatario_bairro,
            destinatario_cidade=m.destinatario_cidade,
            destinatario_estado=m.destinatario_estado,
            destinatario_pais=m.destinatario_pais,
            destinatario_cep=m.destinatario_cep,
            transportadora_cnpj=m.transportadora_cnpj,
            observacao=m.observacao,
            nota_fiscal_origem=m.nota_fiscal_origem,
            serie_origem=m.serie_origem,
            chave_acesso_origem=m.chave_acesso_origem,
            tipo_ambiente_nfe=m.tipo_ambiente_nfe,
            protocolo=m.protocolo,
            cfop=m.cfop,
            quantidade=m.quantidade,
            valor_desconto=m.valor_desconto,
            valor_total_produtos=m.valor_total_produtos,
            valor_total_nota=m.valor_total_nota,
            data_cancelamento=m.data_cancelamento,
            data_autorizacao=m.data_autorizacao,
            estoque_tipo=m.estoque_tipo,
            status=m.status,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[NotaFiscalEntity]:
        results = self._db.scalars(select(NotaFiscal)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, nota_fiscal_id: int) -> Optional[NotaFiscalEntity]:
        result = self._db.scalars(
            select(NotaFiscal).where(NotaFiscal.id == nota_fiscal_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_pedido_id(self, pedido_id: int) -> list[NotaFiscalEntity]:
        results = self._db.scalars(
            select(NotaFiscal).where(NotaFiscal.pedido_id == pedido_id)
        ).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_chave_acesso(self, chave_acesso: str) -> Optional[NotaFiscalEntity]:
        result = self._db.scalars(
            select(NotaFiscal).where(NotaFiscal.chave_acesso == chave_acesso)
        ).first()
        return self._map_to_entity(result) if result else None

    def create(self, nota_fiscal: NotaFiscalEntity) -> NotaFiscalEntity:
        db_obj = NotaFiscal(
            nota_id=nota_fiscal.nota_id,
            chave_acesso=nota_fiscal.chave_acesso,
            versao=nota_fiscal.versao,
            especie=nota_fiscal.especie,
            modelo=nota_fiscal.modelo,
            numero=nota_fiscal.numero,
            serie=nota_fiscal.serie,
            data_emissao=nota_fiscal.data_emissao,
            data_entrega=nota_fiscal.data_entrega,
            pedido_id=nota_fiscal.pedido_id,
            tipo_pedido=nota_fiscal.tipo_pedido,
            tipo_nota=nota_fiscal.tipo_nota,
            situacao=nota_fiscal.situacao,
            emitente_cnpj=nota_fiscal.emitente_cnpj,
            destinatario_cnpj=nota_fiscal.destinatario_cnpj,
            destinatario_nome=nota_fiscal.destinatario_nome,
            tipo_ambiente_nfe=nota_fiscal.tipo_ambiente_nfe,
            protocolo=nota_fiscal.protocolo,
            cfop=nota_fiscal.cfop,
            quantidade=nota_fiscal.quantidade,
            valor_desconto=nota_fiscal.valor_desconto,
            valor_total_produtos=nota_fiscal.valor_total_produtos,
            valor_total_nota=nota_fiscal.valor_total_nota,
            estoque_tipo=nota_fiscal.estoque_tipo,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, nota_fiscal: NotaFiscalEntity) -> NotaFiscalEntity:
        result = self._db.scalars(
            select(NotaFiscal).where(NotaFiscal.id == nota_fiscal.id)
        ).first()
        if result is None:
            raise ValueError(f"NotaFiscal with id={nota_fiscal.id} not found.")
        result.situacao = nota_fiscal.situacao
        result.data_cancelamento = nota_fiscal.data_cancelamento
        result.data_entrega = nota_fiscal.data_entrega
        result.valor_total_nota = nota_fiscal.valor_total_nota
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, nota_fiscal_id: int) -> None:
        result = self._db.scalars(
            select(NotaFiscal).where(NotaFiscal.id == nota_fiscal_id)
        ).first()
        if result is not None:
            result.status = False
            self._db.commit()


# ═══════════════════════════════════════════════════════════════════════
#  NotaFiscalItemRepository
# ═══════════════════════════════════════════════════════════════════════

class NotaFiscalItemRepository(NotaFiscalItemRepositoryProtocol):
    """Repositório para persistência de NotaFiscalItem no PostgreSQL."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _map_to_entity(m: NotaFiscalItem) -> NotaFiscalItemEntity:
        return NotaFiscalItemEntity(
            id=m.id,
            notafiscal_id=m.notafiscal_id,
            sequencia=m.sequencia,
            produto=m.produto,
            caixa=m.caixa,
            lote=m.lote,
            quantidade=m.quantidade,
            cfop=m.cfop,
            ncm=m.ncm,
            valor_bruto=m.valor_bruto,
            valor_desconto=m.valor_desconto,
            valor_liquido=m.valor_liquido,
            valor_total_produto=m.valor_total_produto,
            valor_aliquota_icms=m.valor_aliquota_icms,
            valor_aliquota_ipi=m.valor_aliquota_ipi,
            valor_aliquota_pis=m.valor_aliquota_pis,
            valor_aliquota_cofins=m.valor_aliquota_cofins,
            data_validade=m.data_validade,
            ean=m.ean,
            volume=m.volume,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def get_all(self) -> list[NotaFiscalItemEntity]:
        results = self._db.scalars(select(NotaFiscalItem)).all()
        return [self._map_to_entity(r) for r in results]

    def get_by_id(self, item_id: int) -> Optional[NotaFiscalItemEntity]:
        result = self._db.scalars(
            select(NotaFiscalItem).where(NotaFiscalItem.id == item_id)
        ).first()
        return self._map_to_entity(result) if result else None

    def get_by_notafiscal_id(self, notafiscal_id: int) -> list[NotaFiscalItemEntity]:
        results = self._db.scalars(
            select(NotaFiscalItem).where(NotaFiscalItem.notafiscal_id == notafiscal_id)
        ).all()
        return [self._map_to_entity(r) for r in results]

    def create(self, item: NotaFiscalItemEntity) -> NotaFiscalItemEntity:
        db_obj = NotaFiscalItem(
            notafiscal_id=item.notafiscal_id,
            sequencia=item.sequencia,
            produto=item.produto,
            caixa=item.caixa,
            lote=item.lote,
            quantidade=item.quantidade,
            cfop=item.cfop,
            ncm=item.ncm,
            valor_bruto=item.valor_bruto,
            valor_desconto=item.valor_desconto,
            valor_liquido=item.valor_liquido,
            valor_total_produto=item.valor_total_produto,
            valor_aliquota_icms=item.valor_aliquota_icms,
            valor_aliquota_ipi=item.valor_aliquota_ipi,
            valor_aliquota_pis=item.valor_aliquota_pis,
            valor_aliquota_cofins=item.valor_aliquota_cofins,
            ean=item.ean,
            volume=item.volume,
        )
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return self._map_to_entity(db_obj)

    def update(self, item: NotaFiscalItemEntity) -> NotaFiscalItemEntity:
        result = self._db.scalars(
            select(NotaFiscalItem).where(NotaFiscalItem.id == item.id)
        ).first()
        if result is None:
            raise ValueError(f"NotaFiscalItem with id={item.id} not found.")
        result.quantidade = item.quantidade
        result.valor_bruto = item.valor_bruto
        result.valor_desconto = item.valor_desconto
        result.valor_liquido = item.valor_liquido
        self._db.commit()
        self._db.refresh(result)
        return self._map_to_entity(result)

    def delete(self, item_id: int) -> None:
        result = self._db.scalars(
            select(NotaFiscalItem).where(NotaFiscalItem.id == item_id)
        ).first()
        if result is not None:
            self._db.delete(result)
            self._db.commit()
