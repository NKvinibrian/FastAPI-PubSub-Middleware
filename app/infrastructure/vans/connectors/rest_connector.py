"""
Conector REST para comunicação com APIs externas.

Implementa o protocolo ApiConnectorProtocol usando httpx.AsyncClient.
Resolve autenticação automaticamente via AuthContext injetado.

Responsabilidade única: transporte HTTP — não conhece banco de dados,
logging ou regras de negócio.
"""

from typing import Any, Optional

import httpx

from app.infrastructure.auth.context import AuthContext
from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol


class RestConnector:
    """
    Conector REST baseado em httpx.

    Resolve autenticação (token) de forma lazy na primeira requisição
    e reutiliza nas chamadas subsequentes.

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
        """
        Resolve o token de autenticação via provider.

        Faz lazy-load: só autentica na primeira chamada e cacheia o resultado.

        Returns:
            Token formatado (ex: 'Bearer xxx').
        """
        if self._token is not None:
            return self._token

        provider = self._auth_context.provider

        # Se o provider já retorna headers direto (ex: BearerAuthProvider)
        result = await provider.build_auth()

        if isinstance(result, dict):
            # BearerAuthProvider retorna dict com "Authorization"
            self._token = result.get("Authorization", "")
        elif isinstance(result, httpx.Request):
            # Providers que retornam um httpx.Request para autenticação
            async with httpx.AsyncClient() as client:
                response = await client.send(result)
                response.raise_for_status()

                if isinstance(provider, BaseAuthProviderProtocol):
                    self._token = provider.build_token_req(response)
                else:
                    self._token = response.text

        return self._token or ""

    async def _build_headers(
        self,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """
        Constrói os headers para a requisição incluindo autenticação.

        Args:
            extra_headers: Headers adicionais opcionais.

        Returns:
            Dicionário de headers prontos para envio.
        """
        token = await self._resolve_token()
        headers: dict[str, str] = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def reset_token(self) -> None:
        """Limpa o token cacheado, forçando re-autenticação na próxima chamada."""
        self._token = None

    async def request(
        self,
        method: str,
        path: str,
        headers: Optional[dict[str, str]] = None,
        payload: Any = None,
        timeout: Optional[int] = None,
    ) -> httpx.Response:
        """
        Executa uma requisição HTTP autenticada.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, etc.).
            path: Caminho relativo ao base_url.
            headers: Headers adicionais (sobrescrevem os padrão).
            payload: Corpo da requisição (dict/list → json, str/bytes → content).
            timeout: Timeout em segundos (sobrescreve o padrão do AuthContext).

        Returns:
            httpx.Response com a resposta do servidor.

        Raises:
            httpx.HTTPStatusError: Se a resposta indicar erro HTTP.
            httpx.RequestError: Se houver erro de conexão/timeout.
        """
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        request_headers = await self._build_headers(headers)
        request_timeout = timeout or self.timeout

        async with httpx.AsyncClient() as client:
            if isinstance(payload, (dict, list)):
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=payload,
                    timeout=request_timeout,
                )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    content=payload,
                    timeout=request_timeout,
                )

        return response

