"""
Protocolos para conectores de transporte de VANs.

Define os contratos (interfaces) que devem ser implementados pelos
conectores de comunicação com sistemas externos (REST, GraphQL, FTP, etc.).

Os conectores são a camada de transporte pura — não conhecem
banco de dados, logging ou regras de negócio.
"""

from typing import Protocol, Any, Optional, Union
from io import BytesIO


class ApiConnectorProtocol(Protocol):
    """
    Protocolo para conectores de API (REST, GraphQL, etc.).

    Define a interface mínima para realizar requisições HTTP
    autenticadas contra sistemas externos.
    """

    async def request(
        self,
        method: str,
        path: str,
        headers: Optional[dict[str, str]] = None,
        payload: Any = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Executa uma requisição HTTP.

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE, etc.).
            path: Caminho relativo ao base_url do conector.
            headers: Headers adicionais para a requisição.
            payload: Corpo da requisição (dict, str, bytes).
            timeout: Timeout da requisição em segundos (sobrescreve o padrão).

        Returns:
            Resposta HTTP (httpx.Response).
        """
        ...


class GraphQLConnectorProtocol(Protocol):
    """
    Protocolo para conectores GraphQL.

    Define a interface para executar queries e mutations
    GraphQL autenticadas.
    """

    async def execute(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Executa uma query/mutation GraphQL.

        Args:
            query: String da query ou mutation GraphQL.
            variables: Variáveis para a query.
            operation_name: Nome da operação (se houver múltiplas).
            extra_headers: Headers extras para esta requisição.

        Returns:
            Dicionário com os dados retornados (campo "data" da resposta).
        """
        ...


class FileConnectorProtocol(Protocol):
    """
    Protocolo para conectores de arquivo (FTP, Bucket, SFTP, etc.).

    Define a interface para operações de leitura/escrita de arquivos
    em sistemas de armazenamento remoto. Suporta context manager.
    """

    def open(self) -> None:
        """Abre a conexão com o sistema remoto."""
        ...

    def close(self) -> None:
        """Encerra a conexão com o sistema remoto."""
        ...

    def list_files(self, path: Optional[str] = None) -> list[str]:
        """
        Lista os arquivos em um diretório remoto.

        Args:
            path: Caminho do diretório. Se None, usa o diretório atual.

        Returns:
            Lista de nomes de arquivos.
        """
        ...

    def get_file(self, remote_path: str) -> BytesIO:
        """
        Baixa um arquivo remoto.

        Args:
            remote_path: Caminho completo do arquivo no servidor remoto.

        Returns:
            Conteúdo do arquivo como BytesIO.
        """
        ...

    def send_file(self, remote_path: str, content: Union[bytes, BytesIO]) -> None:
        """
        Envia um arquivo para o servidor remoto.

        Args:
            remote_path: Caminho de destino no servidor remoto.
            content: Conteúdo do arquivo em bytes ou BytesIO.
        """
        ...

    def delete_file(self, remote_path: str) -> None:
        """
        Remove um arquivo do servidor remoto.

        Args:
            remote_path: Caminho do arquivo a ser removido.
        """
        ...

    def __enter__(self) -> "FileConnectorProtocol":
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        ...

