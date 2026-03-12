"""
Fetcher para arquivos remotos (FTP, Bucket, etc.).

Orquestra a busca/envio de arquivos utilizando um FileConnector injetado.
Suporta context manager para gerenciar o ciclo de vida da conexão.

Não conhece banco de dados, logging ou regras de negócio — delega
o transporte inteiramente ao conector.
"""

from io import BytesIO
from typing import Optional, Union

from app.domain.protocol.vans.connector import FileConnectorProtocol


class FileFetcher:
    """
    Fetcher de arquivos que delega operações ao FileConnector.

    Suporta context manager para abertura/fechamento automático.

    Attributes:
        _connector: Conector de arquivo (FTP, Bucket, etc.).
    """

    def __init__(self, connector: FileConnectorProtocol) -> None:
        self._connector = connector

    def fetch(self, remote_path: str) -> BytesIO:
        """
        Busca (download) um arquivo remoto.

        Args:
            remote_path: Caminho completo do arquivo no servidor remoto.

        Returns:
            Conteúdo do arquivo como BytesIO.
        """
        return self._connector.get_file(remote_path)

    def send(self, remote_path: str, content: Union[bytes, BytesIO]) -> None:
        """
        Envia (upload) um arquivo para o servidor remoto.

        Args:
            remote_path: Caminho de destino no servidor.
            content: Conteúdo do arquivo em bytes ou BytesIO.
        """
        self._connector.send_file(remote_path, content)

    def list_files(self, path: Optional[str] = None) -> list[str]:
        """
        Lista arquivos em um diretório remoto.

        Args:
            path: Caminho do diretório. Se None, usa o diretório atual.

        Returns:
            Lista de nomes de arquivos.
        """
        return self._connector.list_files(path)

    def delete(self, remote_path: str) -> None:
        """
        Remove um arquivo do servidor remoto.

        Args:
            remote_path: Caminho do arquivo a ser removido.
        """
        self._connector.delete_file(remote_path)

    def __enter__(self) -> "FileFetcher":
        self._connector.open()
        return self

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        self._connector.close()

