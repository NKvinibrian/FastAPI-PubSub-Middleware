from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey, UUID, BigInteger,
)
from sqlalchemy.orm import relationship

from app.infrastructure.db.models.default_datahub.default_table import DefaultAttributesModel
from app.infrastructure.db import Base


class PrePedido(Base, DefaultAttributesModel):
    __tablename__ = "pre_pedidos"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, comment="Identificador do pré-pedido")
    origem_sistema_id = Column(String, comment="Id do pedido no sistema transacional", nullable=True)
    origem_industria_pedido_id = Column(String, comment="Número do Pedido na indústria", nullable=True)
    origem_industria_codigo = Column(String, comment="Sigla do Projeto", nullable=True)
    tipo_pedido = Column(String, comment="Tipo do pedido", nullable=True)
    origem_sistema = Column(String, comment="Ex: fidelize_funcional", nullable=True)
    origem_industria = Column(String, comment="EX: MSD / ASTRAZENECA", nullable=True)
    origem_log_uuid = Column(UUID, comment="Registro de log da entrada desse pedido", nullable=True)
    origem_industria_created_at = Column(DateTime, comment="Data de Criação na indústria", nullable=True)
    informacoes_adicionais = Column(String, comment="Informações adicionais", nullable=True)
    observacao = Column(String, comment="Observação", nullable=True)
    distribuidor_cnpj = Column(String, comment="CNPJ do distribuidor", nullable=True)
    prazo_negociado = Column(String, comment="Prazo Negociado", nullable=True)
    condicao_comercial = Column(String, comment="Condição Comercial", nullable=True)
    margem = Column(Float, comment="Margem", nullable=True)
    pedido_bonificado = Column(Boolean, comment="Pedido Bonificado", nullable=True)
    entrega_programada = Column(Boolean, comment="Entrega Programada", nullable=True)
    tipo_origem = Column(String, comment="Ex: Canal Autorizador, Tradetools, Delivery", nullable=True)
    distribuidor_filial_cnpj = Column(String, comment="CNPJ da Filial do Distribuidor", nullable=True)
    distribuidor_matriz_cnpj = Column(String, comment="CNPJ da Matriz do Distribuidor", nullable=True)
    vendedor_codigo = Column(String, comment="Código do vendedor", nullable=True)
    nf_confirmed = Column(Boolean, comment="Status que indica recebimento da NF no Datahub", nullable=True)
    tipo_faturamento = Column(String, comment="Ex: Dentro do Estado / Fora do Estado", nullable=True)
    cliente_codigo = Column(String, comment="Código do Pedido no Cliente", nullable=True)
    cliente_email = Column(String, comment="Email do cliente", nullable=True)
    cliente_tipo = Column(String, comment="Tipo do cliente: PJ / PF", nullable=True)
    cliente_nome_fantasia = Column(String, comment="Nome fantasia do cliente", nullable=True)
    cliente_razao_social = Column(String, comment="Razão social do cliente", nullable=True)
    cliente_telefone = Column(String, comment="Telefone do cliente", nullable=True)
    cliente_inscricao_estadual = Column(String, comment="Inscrição estadual do cliente", nullable=True)
    cliente_cpf_cnpj = Column(String, comment="CPF ou CNPJ do cliente", nullable=True)
    entrega_rua = Column(String, comment="Rua de entrega", nullable=True)
    entrega_numero = Column(String, comment="Número de entrega", nullable=True)
    entrega_bairro = Column(String, comment="Bairro de entrega", nullable=True)
    entrega_complemento = Column(String, comment="Complemento do endereço de entrega", nullable=True)
    entrega_observacao = Column(String, comment="Observacao do endereço de entrega", nullable=True)
    entrega_cidade = Column(String, comment="Cidade de entrega", nullable=True)
    entrega_estado = Column(String, comment="Estado de entrega", nullable=True)
    entrega_cep = Column(String, comment="CEP de entrega", nullable=True)
    destinatario_nome = Column(String, comment="Nome do destinatário", nullable=True)
    destinario_cpf_cnpj = Column(String, comment="CPF ou CNPJ do destinatário", nullable=True)
    entrega_status = Column(String, comment="Status de entrega: DISPATCHED, ON_DELIVERY_ROUTE, DELIVERED", nullable=True)
    erp_confirmed = Column(Boolean, comment="Atendimento Confirmado no Datasul", nullable=True)
    vans_confirmed = Column(Boolean, comment="Atendimento Confirmado na Van", nullable=True)
    delivery_at = Column(DateTime, comment="Data de envio para entrega", nullable=True)
    delivered_at = Column(DateTime, comment="Data de entrega concluída", nullable=True)
    fetched_at = Column(DateTime, comment="Data de captura do pedido", nullable=True)
    erp_sended = Column(Boolean, comment="Enviado ao Datasul", nullable=True)
    erp_returned = Column(Boolean, comment="Retornou do Datasul?", nullable=True)
    motivo_atendimento = Column(String, comment="Motivo de Atendimento de Pedido", nullable=True)
    message_id = Column(BigInteger, comment="ID da mensagem PubSub", nullable=True)
    order_cancellation_sent = Column(Boolean, comment="Enviado Cancelamento de Pedido para Van", nullable=True)
    central_processos_id = Column(String, comment="Código da Central de Processos", nullable=True)

    itens = relationship("PrePedidoItem", back_populates="pre_pedido", cascade="all, delete-orphan")
    faturamentos = relationship("PrePedidoFaturamento", back_populates="pre_pedido", cascade="all, delete-orphan")


class PrePedidoFaturamento(Base):
    __tablename__ = "pre_pedido_faturamentos"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, comment="Identificador do faturamento")
    pre_pedido_id = Column(Integer, ForeignKey("hub.pre_pedidos.id"), nullable=False, comment="Referência ao pré-pedido")
    tipo_pagamento_id = Column(Integer, comment="Identificador do tipo de pagamento", nullable=True)
    tipo_pagamento = Column(String, comment="Ex: Á vista", nullable=True)
    prazo_pagamento_id = Column(Integer, comment="Identificador do prazo de pagamento", nullable=True)
    prazo_pagamento = Column(String, comment="Prazo de pagamento", nullable=True)
    numero_dias_prazo = Column(Integer, comment="Número de dias do prazo", nullable=True)
    pedido_num_bonificacao = Column(String, comment="Número do pedido que gerou bonificação", nullable=True)

    pre_pedido = relationship("PrePedido", back_populates="faturamentos")


class PrePedidoItem(Base):
    __tablename__ = "pre_pedido_itens"
    __table_args__ = {"schema": "hub"}

    id = Column(Integer, primary_key=True, comment="Identificador do item do pré-pedido")
    pre_pedido_id = Column(Integer, ForeignKey("hub.pre_pedidos.id"), nullable=False, comment="Referência ao pré-pedido")
    ean = Column(String, comment="Código EAN do Produto", nullable=False)
    valor_bruto = Column(Float, comment="Valor bruto do Produto", nullable=True)
    quantidade = Column(Integer, comment="Quantidade", nullable=False)
    desconto_percentual = Column(Float, comment="Desconto percentual dado", nullable=True)
    desconto_valor = Column(Float, comment="Desconto em valor", nullable=True)
    valor_liquido = Column(Float, comment="Valor Líquido", nullable=True)
    produto_monitorado = Column(Boolean, comment="É produto monitorado?", nullable=True)
    observacao = Column(String, comment="Observação do item", nullable=True)
    prazo = Column(String, comment="Prazo do item", nullable=True)
    motivo_atendimento = Column(String, comment="Motivo de Atendimento de Pedido", nullable=True)

    pre_pedido = relationship("PrePedido", back_populates="itens")
