"""
Fetcher para APIs GraphQL.

Orquestra a busca de dados utilizando um GraphQLConnector injetado.
Adiciona funcionalidades de extração de dados aninhados sobre
o transporte puro do conector.
"""

from typing import Any, Optional

from app.infrastructure.vans.connectors.graphql_connector import GraphQLConnector


class GraphQLFetcher:
    """
    Fetcher GraphQL que delega requisições ao GraphQLConnector.

    Adiciona capacidade de navegar em dados aninhados via extract_path.

    Attributes:
        _connector: Instância de GraphQLConnector já configurada com AuthContext.
    """

    def __init__(self, connector: GraphQLConnector) -> None:
        self._connector = connector

    async def fetch(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
        extract_path: Optional[list[str]] = None,
        url: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Busca dados via GraphQL.

        Args:
            query: Query ou mutation GraphQL.
            variables: Variáveis da query.
            operation_name: Nome da operação.
            extra_headers: Headers extras.
            extract_path: Lista de chaves para navegar no resultado.
                Ex: ["createOrder", "items"] navega em data["createOrder"]["items"].
            url: Sobrescreve a URL alvo no conector (vinda de request_details).

        Returns:
            Dicionário com os dados retornados (campo "data" ou sub-caminho).

        Raises:
            RuntimeError: Se a resposta contiver erros GraphQL.
            KeyError: Se extract_path não puder ser resolvido.
        """
        data = await self._connector.execute(
            query=query,
            variables=variables,
            operation_name=operation_name,
            extra_headers=extra_headers,
            url=url,
        )

        if extract_path and data:
            node: Any = data
            for key in extract_path:
                if not isinstance(node, dict):
                    raise KeyError(
                        f"Cannot extract path {extract_path}, stuck at '{key}'"
                    )
                node = node.get(key, {})
            return node

        return data

