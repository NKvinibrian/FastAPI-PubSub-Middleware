"""
Conector GraphQL para comunicação com APIs GraphQL externas.

Implementa o protocolo GraphQLConnectorProtocol usando httpx.AsyncClient.
Resolve autenticação automaticamente via AuthContext injetado.

Responsabilidade única: transporte GraphQL — não conhece banco de dados,
logging ou regras de negócio.
"""

from typing import Any, Optional

import httpx

from app.infrastructure.auth.context import AuthContext
from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol


class GraphQLConnector:
    """
    Conector GraphQL baseado em httpx.

    Resolve autenticação (token) de forma lazy e executa
    queries/mutations GraphQL.

    Attributes:
        _auth_context: Contexto de autenticação com provider, base_url e timeout.
        _token: Token de autenticação cacheado.
    """

    def __init__(self, auth_context: AuthContext) -> None:
        self._auth_context = auth_context
        self._token: Optional[str] = None

    @property
    def base_url(self) -> str:
        return self._auth_context.base_url

    @property
    def timeout(self) -> int:
        return self._auth_context.timeout

    async def _resolve_token(self) -> str:
        """Resolve o token de autenticação via provider (lazy-load + cache)."""
        if self._token is not None:
            return self._token

        provider = self._auth_context.provider
        result = await provider.build_auth()

        if isinstance(result, dict):
            self._token = result.get("Authorization", "")
        elif isinstance(result, httpx.Request):
            async with httpx.AsyncClient() as client:
                response = await client.send(result)
                response.raise_for_status()

                if isinstance(provider, BaseAuthProviderProtocol):
                    self._token = provider.build_token_req(response)
                else:
                    self._token = response.text

        return self._token or ""

    def reset_token(self) -> None:
        """Limpa o token cacheado, forçando re-autenticação na próxima chamada."""
        self._token = None

    async def execute(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
        url: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Executa uma query/mutation GraphQL autenticada.

        Args:
            query: String da query ou mutation GraphQL.
            variables: Variáveis para a query.
            operation_name: Nome da operação (se houver múltiplas no documento).
            extra_headers: Headers extras para esta requisição específica.
            url: Sobrescreve a URL alvo. Se None, usa `self.base_url`.

        Returns:
            Dicionário com os dados retornados (campo "data" da resposta GraphQL).

        Raises:
            RuntimeError: Se a resposta contiver erros GraphQL.
            httpx.HTTPStatusError: Se a resposta HTTP indicar erro.
        """
        token = await self._resolve_token()

        headers: dict[str, str] = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        if operation_name is not None:
            payload["operationName"] = operation_name

        target_url = url or self.base_url

        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()

        if "errors" in body:
            raise RuntimeError(f"GraphQL errors: {body['errors']}")

        return body.get("data", {})

