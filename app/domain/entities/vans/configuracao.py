from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProjetoSiglasEntity:
    id: Optional[int] = None
    projeto_sigla: Optional[str] = None
    descricao_industria: Optional[str] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OrigemSistemasEntity:
    id: Optional[int] = None
    origem_sistema: Optional[str] = None
    descricao: Optional[str] = None
    observacao: Optional[str] = None
    is_pbm: Optional[bool] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ProjetoSiglaOrigemEntity:
    id: Optional[int] = None
    projeto_sigla_id: Optional[int] = None
    origem_sistema_id: Optional[int] = None
    status: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
