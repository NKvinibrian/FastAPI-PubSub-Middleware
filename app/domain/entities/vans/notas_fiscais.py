from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class NotaFiscalEntity:
    id: Optional[int] = None
    nota_id: Optional[int] = None
    chave_acesso: Optional[str] = None
    versao: Optional[str] = None
    especie: Optional[str] = None
    modelo: Optional[str] = None
    numero: Optional[int] = None
    serie: Optional[str] = None
    data_emissao: Optional[datetime] = None
    data_entrega: Optional[date] = None
    pedido_id: Optional[int] = None
    tipo_pedido: Optional[int] = None
    tipo_nota: Optional[str] = None
    situacao: Optional[str] = None
    emitente_cnpj: Optional[str] = None
    destinatario_cnpj: Optional[str] = None
    destinatario_nome: Optional[str] = None
    destinatario_logradouro: Optional[str] = None
    destinatario_numero: Optional[str] = None
    destinatario_complemento: Optional[str] = None
    destinatario_bairro: Optional[str] = None
    destinatario_cidade: Optional[str] = None
    destinatario_estado: Optional[str] = None
    destinatario_pais: Optional[str] = None
    destinatario_cep: Optional[str] = None
    transportadora_cnpj: Optional[str] = None
    observacao: Optional[str] = None
    nota_fiscal_origem: Optional[int] = None
    serie_origem: Optional[str] = None
    chave_acesso_origem: Optional[str] = None
    tipo_ambiente_nfe: Optional[int] = None
    protocolo: Optional[str] = None
    cfop: Optional[int] = None
    quantidade: Optional[float] = None
    valor_desconto: Optional[float] = None
    valor_total_produtos: Optional[float] = None
    valor_total_nota: Optional[float] = None
    data_cancelamento: Optional[datetime] = None
    data_autorizacao: Optional[datetime] = None
    estoque_tipo: Optional[str] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class NotaFiscalItemEntity:
    id: Optional[int] = None
    notafiscal_id: Optional[int] = None
    sequencia: Optional[int] = None
    produto: Optional[int] = None
    caixa: Optional[int] = None
    lote: Optional[str] = None
    quantidade: Optional[float] = None
    cfop: Optional[int] = None
    ncm: Optional[str] = None
    valor_bruto: Optional[float] = None
    valor_desconto: Optional[float] = None
    valor_liquido: Optional[float] = None
    valor_total_produto: Optional[float] = None
    valor_aliquota_icms: Optional[float] = None
    valor_aliquota_ipi: Optional[float] = None
    valor_aliquota_pis: Optional[float] = None
    valor_aliquota_cofins: Optional[float] = None
    data_validade: Optional[date] = None
    ean: Optional[str] = None
    volume: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
