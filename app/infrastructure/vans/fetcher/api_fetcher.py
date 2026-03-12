"""
Fetcher para APIs REST.

Orquestra a busca de dados utilizando um RestConnector injetado.
Não conhece autenticação, banco de dados ou logging — delega
o transporte inteiramente ao conector.
"""

from typing import Any, Optional

import httpx

from app.infrastructure.vans.connectors.rest_connector import RestConnector


class ApiFetcher:
    """
    Fetcher REST que delega requisições ao RestConnector.

    Attributes:
        _connector: Instância de RestConnector já configurada com AuthContext.
    """

    def __init__(self, connector: RestConnector) -> None:
        self._connector = connector

    async def fetch(
        self,
        method: str,
        path: str,
        headers: Optional[dict[str, str]] = None,
        payload: Any = None,
        timeout: Optional[int] = None,
    ) -> httpx.Response:
        """
        Busca dados via API REST.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, etc.).
            path: Caminho relativo ao base_url do conector.
            headers: Headers adicionais.
            payload: Corpo da requisição (dict/list → json, str/bytes → content).
            timeout: Timeout em segundos (sobrescreve o padrão).

        Returns:
            httpx.Response com a resposta do servidor.
        """
        return await self._connector.request(
            method=method,
            path=path,
            headers=headers,
            payload=payload,
            timeout=timeout,
        )

    async def fetch_json(
        self,
        method: str,
        path: str,
        headers: Optional[dict[str, str]] = None,
        payload: Any = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Busca dados via API REST e retorna o JSON parseado.

        Atalho para fetch() + response.json().

        Returns:
            Dados JSON parseados (dict ou list).

        Raises:
            httpx.HTTPStatusError: Se a resposta indicar erro HTTP.
        """
        response = await self.fetch(
            method=method,
            path=path,
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

