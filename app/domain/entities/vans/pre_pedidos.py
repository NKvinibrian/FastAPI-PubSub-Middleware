from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class PrePedidoEntity:
    id: Optional[int] = None
    origem_sistema_id: Optional[str] = None
    origem_industria_pedido_id: Optional[str] = None
    origem_industria_codigo: Optional[str] = None
    tipo_pedido: Optional[str] = None
    origem_sistema: Optional[str] = None
    origem_industria: Optional[str] = None
    origem_log_uuid: Optional[UUID] = None
    origem_industria_created_at: Optional[datetime] = None
    informacoes_adicionais: Optional[str] = None
    observacao: Optional[str] = None
    status: Optional[bool] = None
    distribuidor_cnpj: Optional[str] = None
    prazo_negociado: Optional[str] = None
    condicao_comercial: Optional[str] = None
    margem: Optional[float] = None
    pedido_bonificado: Optional[bool] = None
    entrega_programada: Optional[bool] = None
    tipo_origem: Optional[str] = None
    distribuidor_filial_cnpj: Optional[str] = None
    distribuidor_matriz_cnpj: Optional[str] = None
    vendedor_codigo: Optional[str] = None
    nf_confirmed: Optional[bool] = None
    tipo_faturamento: Optional[str] = None
    cliente_codigo: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_tipo: Optional[str] = None
    cliente_nome_fantasia: Optional[str] = None
    cliente_razao_social: Optional[str] = None
    cliente_telefone: Optional[str] = None
    cliente_inscricao_estadual: Optional[str] = None
    cliente_cpf_cnpj: Optional[str] = None
    entrega_rua: Optional[str] = None
    entrega_numero: Optional[str] = None
    entrega_bairro: Optional[str] = None
    entrega_complemento: Optional[str] = None
    entrega_observacao: Optional[str] = None
    entrega_cidade: Optional[str] = None
    entrega_estado: Optional[str] = None
    entrega_cep: Optional[str] = None
    destinatario_nome: Optional[str] = None
    destinario_cpf_cnpj: Optional[str] = None
    entrega_status: Optional[str] = None
    erp_confirmed: Optional[bool] = None
    vans_confirmed: Optional[bool] = None
    delivery_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    erp_sended: Optional[bool] = None
    erp_returned: Optional[bool] = None
    motivo_atendimento: Optional[str] = None
    message_id: Optional[int] = None
    order_cancellation_sent: Optional[bool] = None
    central_processos_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PrePedidoItemEntity:
    id: Optional[int] = None
    pre_pedido_id: Optional[int] = None
    ean: Optional[str] = None
    valor_bruto: Optional[float] = None
    quantidade: Optional[int] = None
    desconto_percentual: Optional[float] = None
    desconto_valor: Optional[float] = None
    valor_liquido: Optional[float] = None
    produto_monitorado: Optional[bool] = None
    observacao: Optional[str] = None
    prazo: Optional[str] = None
    motivo_atendimento: Optional[str] = None


@dataclass
class PrePedidoFaturamentoEntity:
    id: Optional[int] = None
    pre_pedido_id: Optional[int] = None
    tipo_pagamento_id: Optional[int] = None
    tipo_pagamento: Optional[str] = None
    prazo_pagamento_id: Optional[int] = None
    prazo_pagamento: Optional[str] = None
    numero_dias_prazo: Optional[int] = None
    pedido_num_bonificacao: Optional[str] = None
