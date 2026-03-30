from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Date, DateTime, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from app.infrastructure.db import Base


class Pedido(Base, DefaultAttributesModel):
    __tablename__ = "pedidos"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido_datasul = Column(Integer, nullable=False)
    origem = Column(String, nullable=False)
    filial_cnpj = Column(String, nullable=False)
    filial_id = Column(String, nullable=False)
    data_emissao = Column(Date, nullable=False)
    pedido_tipo = Column(Integer, nullable=False)
    condicao_pagamento = Column(Integer, nullable=False)
    obs = Column(String, nullable=True)
    pedido_num = Column(Integer, nullable=True)
    valor_pedido = Column(Float, nullable=True)
    percentual_desconto = Column(Float, nullable=True)
    valor_desconto = Column(Float, nullable=True)
    valor_bruto = Column(Float, nullable=True)
    cliente_id = Column(String, nullable=False)
    entidade_tipo = Column(Integer, nullable=False)
    base_origem = Column(Integer, nullable=False)
    pedido_info = Column(String, nullable=True)
    codigo_etapa = Column(Integer, nullable=True)
    descricao_etapa = Column(String, nullable=True)
    data_etapa = Column(DateTime, nullable=True)
    ordem_compra_id = Column(String, nullable=True)
    motivo_cancelamento = Column(String, nullable=True)
    data_shelf_life = Column(Integer, nullable=True)
    estoque_tipo = Column(String, nullable=True)
    motivo_atendimento = Column(String, comment="Motivo de Atendimento de Pedido", nullable=True)
    cnpj_transportadora = Column(String, comment="CNPJ da Transportadora do Pedido", nullable=True)
    nome_transportadora = Column(String, comment="Nome da Transportadora do Pedido", nullable=True)
    is_pbm = Column(Boolean, nullable=True, default=False)

    itens = relationship("PedidoItem", back_populates="pedido")


class PedidoItem(Base):
    __tablename__ = "pedidos_itens"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido_datasul = Column(Integer, nullable=False)
    sequencia_id = Column(Integer, nullable=False)
    pedido_id = Column(Integer, ForeignKey("hub.pedidos.id"), nullable=False)
    produto_id = Column(Integer, nullable=False)
    lote_id = Column(Integer, nullable=True)
    lote = Column(String, nullable=True)
    lote_cdi = Column(Integer, nullable=True)
    lote_quantidade_saida = Column(Float, nullable=True)
    documento_num = Column(Integer, nullable=True)
    numero_fornecedor = Column(String, nullable=True)
    data_validade = Column(Date, nullable=True)
    data_fabricacao = Column(Date, nullable=True)
    quantidade_original = Column(Float, nullable=True)
    quantidade = Column(Float, nullable=False)
    quantidade_convertida = Column(Float, nullable=True)
    quantidade_faturar = Column(Float, nullable=True)
    quantidade_reservada = Column(Float, nullable=True)
    tipo_embalagem = Column(String, nullable=True)
    valor_unitario = Column(Float, nullable=False)
    percentual_desconto = Column(Float, nullable=True)
    valor_desconto = Column(Float, nullable=False)
    valor_bruto = Column(Float, nullable=True)
    valor_total_liquido = Column(Float, nullable=True)
    valor_total_bruto = Column(Float, nullable=True)
    valor_total_desconto = Column(Float, nullable=True)
    observacao = Column(String, nullable=True)
    data_alteracao = Column(Date, nullable=True)
    valor_frete = Column(Float, nullable=True)
    data_entrega = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    data_shelf_life = Column(Integer, nullable=True)
    status = Column(Boolean, default=True, nullable=True)
    motivo_atendimento = Column(String, comment="Motivo de Atendimento de Pedido", nullable=True)

    pedido = relationship("Pedido", back_populates="itens")


class PedidoComplementoVans(Base, DefaultAttributesModel):
    __tablename__ = "pedidos_complemento_vans"
    __table_args__ = (
        UniqueConstraint(
            "id_pedido_datasul",
            "origem_van",
            name="uq_pedido_datasul_origem",
        ),
        {"schema": "hub"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido_datasul = Column(Integer, nullable=False, index=True)
    id_pedido_vans = Column(String, nullable=True, index=True)
    extra_data = Column(JSON, nullable=True)
    origem_van = Column(String, nullable=False)
    status_atual = Column(String, nullable=True)
    status_atual_van = Column(String, nullable=True)
    is_finished = Column(Boolean, nullable=True, default=False)
