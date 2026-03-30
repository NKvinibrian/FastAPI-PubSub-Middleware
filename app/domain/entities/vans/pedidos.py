from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional


@dataclass
class PedidoEntity:
    id: Optional[int] = None
    id_pedido_datasul: Optional[int] = None
    origem: Optional[str] = None
    filial_cnpj: Optional[str] = None
    filial_id: Optional[str] = None
    data_emissao: Optional[date] = None
    pedido_tipo: Optional[int] = None
    condicao_pagamento: Optional[int] = None
    obs: Optional[str] = None
    pedido_num: Optional[int] = None
    valor_pedido: Optional[float] = None
    percentual_desconto: Optional[float] = None
    valor_desconto: Optional[float] = None
    valor_bruto: Optional[float] = None
    cliente_id: Optional[str] = None
    entidade_tipo: Optional[int] = None
    base_origem: Optional[int] = None
    pedido_info: Optional[str] = None
    codigo_etapa: Optional[int] = None
    descricao_etapa: Optional[str] = None
    data_etapa: Optional[datetime] = None
    ordem_compra_id: Optional[str] = None
    motivo_cancelamento: Optional[str] = None
    data_shelf_life: Optional[int] = None
    estoque_tipo: Optional[str] = None
    motivo_atendimento: Optional[str] = None
    cnpj_transportadora: Optional[str] = None
    nome_transportadora: Optional[str] = None
    is_pbm: Optional[bool] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PedidoItemEntity:
    id: Optional[int] = None
    id_pedido_datasul: Optional[int] = None
    sequencia_id: Optional[int] = None
    pedido_id: Optional[int] = None
    produto_id: Optional[int] = None
    lote_id: Optional[int] = None
    lote: Optional[str] = None
    lote_cdi: Optional[int] = None
    lote_quantidade_saida: Optional[float] = None
    documento_num: Optional[int] = None
    numero_fornecedor: Optional[str] = None
    data_validade: Optional[date] = None
    data_fabricacao: Optional[date] = None
    quantidade_original: Optional[float] = None
    quantidade: Optional[float] = None
    quantidade_convertida: Optional[float] = None
    quantidade_faturar: Optional[float] = None
    quantidade_reservada: Optional[float] = None
    tipo_embalagem: Optional[str] = None
    valor_unitario: Optional[float] = None
    percentual_desconto: Optional[float] = None
    valor_desconto: Optional[float] = None
    valor_bruto: Optional[float] = None
    valor_total_liquido: Optional[float] = None
    valor_total_bruto: Optional[float] = None
    valor_total_desconto: Optional[float] = None
    observacao: Optional[str] = None
    data_alteracao: Optional[date] = None
    valor_frete: Optional[float] = None
    data_entrega: Optional[date] = None
    data_shelf_life: Optional[int] = None
    motivo_atendimento: Optional[str] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PedidoComplementoVansEntity:
    id: Optional[int] = None
    id_pedido_datasul: Optional[int] = None
    id_pedido_vans: Optional[str] = None
    extra_data: Optional[dict[str, Any]] = None
    origem_van: Optional[str] = None
    status_atual: Optional[str] = None
    status_atual_van: Optional[str] = None
    is_finished: Optional[bool] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None