"""
Protocolo para o Fetcher de VANs.

Define o contrato (interface) para o fetcher que orquestra
a busca de dados usando conectores de transporte.

O fetcher é a camada de orquestração — delega o transporte
aos conectores e retorna dados brutos.
"""

from typing import Protocol, Any, Optional, Union
from io import BytesIO


class ApiFetcherProtocol(Protocol):
    """
    Protocolo para fetcher de API (REST/GraphQL).

    Orquestra a busca de dados via conectores de API.
    """

    async def fetch(
        self,
        method: str,
        path: str,
        headers: Optional[dict[str, str]] = None,
        payload: Any = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Busca dados via API.

        Args:
            method: Método HTTP.
            path: Caminho relativo.
            headers: Headers adicionais.
            payload: Corpo da requisição.
            timeout: Timeout em segundos.

        Returns:
            Resposta da API.
        """
        ...


class GraphQLFetcherProtocol(Protocol):
    """
    Protocolo para fetcher GraphQL.

    Orquestra a busca de dados via conector GraphQL.
    """

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
            extract_path: Caminho para extração de dados aninhados.
            url: Sobrescreve a URL alvo.

        Returns:
            Dicionário com os dados retornados.
        """
        ...


class FileFetcherProtocol(Protocol):
    """
    Protocolo para fetcher de arquivos (FTP, Bucket, etc.).

    Orquestra a busca/envio de arquivos via conectores de arquivo.
    """

    def fetch(self, remote_path: str) -> BytesIO:
        """
        Busca um arquivo remoto.

        Args:
            remote_path: Caminho do arquivo no servidor remoto.

        Returns:
            Conteúdo do arquivo como BytesIO.
        """
        ...

    def send(self, remote_path: str, content: Union[bytes, BytesIO]) -> None:
        """
        Envia um arquivo para o servidor remoto.

        Args:
            remote_path: Caminho de destino.
            content: Conteúdo do arquivo.
        """
        ...

    def list_files(self, path: Optional[str] = None) -> list[str]:
        """
        Lista arquivos em um diretório remoto.

        Args:
            path: Caminho do diretório.

        Returns:
            Lista de nomes de arquivos.
        """
        ...

