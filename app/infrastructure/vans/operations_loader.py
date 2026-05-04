"""
Carregador de operações (request_details) para os fetchers de VAN.

Mesmo padrão usado pelo Observer subscriber: cada operação tem uma
linha em hub.request_details com endpoint, método e headers. O fetcher
recebe essas linhas pré-resolvidas (URL final = base_url + endpoint)
para não precisar conhecer o banco.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.infrastructure.repositories.integrations.request_details import (
    RequestDetailsRepository,
)


@dataclass(frozen=True)
class OperationConfig:
    name: str
    url: str
    method: str
    request_type: str
    headers: dict[str, str] = field(default_factory=dict)


def load_operations(
    db: Session,
    integration_id: int,
    base_url: str,
    operation_names: list[str],
) -> dict[str, OperationConfig]:
    """
    Resolve as operações nomeadas em request_details e devolve um
    dict pronto pra ser injetado no fetcher.

    Raises:
        ValueError: se algum dos nomes não estiver cadastrado/ativo.
    """
    repo = RequestDetailsRepository(db=db)
    base = base_url.rstrip("/")
    out: dict[str, OperationConfig] = {}
    for name in operation_names:
        rd = repo.get_by_integration_and_name(integration_id, name)
        if rd is None:
            raise ValueError(
                f"RequestDetails não encontrado | "
                f"integration_id={integration_id} | name={name}"
            )
        out[name] = OperationConfig(
            name=name,
            url=f"{base}{rd.endpoint or ''}",
            method=(rd.request_method or "POST").upper(),
            request_type=(rd.request_type or "GRAPHQL").upper(),
            headers=dict(rd.headers or {}),
        )
    return out
