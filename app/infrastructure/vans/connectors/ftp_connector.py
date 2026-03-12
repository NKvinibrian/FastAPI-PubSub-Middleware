"""
Conector FTP para comunicação com servidores de arquivo.

Implementa o protocolo FileConnectorProtocol usando ftplib.FTP.
Suporta context manager para abertura/fechamento automático da conexão.

Responsabilidade única: transporte FTP — não conhece banco de dados,
logging ou regras de negócio.
"""

import ftplib
import logging
from io import BytesIO
from typing import Optional, Union

logger = logging.getLogger(__name__)


class FTPConnector:
    """
    Conector FTP baseado em ftplib.

    Gerencia a conexão com servidores FTP e fornece
    operações de leitura/escrita de arquivos.

    Attributes:
        _host: Endereço do servidor FTP.
        _port: Porta do servidor.
        _user: Usuário para autenticação (None para anônimo).
        _password: Senha para autenticação.
        _timeout: Timeout da conexão em segundos.
        _ftp: Instância ativa de ftplib.FTP.
    """

    def __init__(
        self,
        host: str,
        port: int = 21,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._timeout = timeout
        self._ftp: Optional[ftplib.FTP] = None

    @property
    def is_connected(self) -> bool:
        """Verifica se a conexão FTP está ativa."""
        return self._ftp is not None

    def open(self) -> None:
        """
        Abre a conexão FTP.

        Conecta no servidor e realiza login (autenticado ou anônimo).

        Raises:
            ftplib.all_errors: Se falhar ao conectar ou autenticar.
        """
        self._ftp = ftplib.FTP()
        self._ftp.connect(self._host, self._port, timeout=self._timeout)

        if self._user and self._password:
            self._ftp.login(self._user, self._password)
        else:
            self._ftp.login()

        logger.info("FTP connected to %s:%s", self._host, self._port)

    def close(self) -> None:
        """
        Encerra a conexão FTP de forma segura.

        Tenta quit() gracioso; se falhar, faz close() forçado.
        """
        if self._ftp is None:
            return

        try:
            self._ftp.quit()
        except ftplib.Error:
            self._ftp.close()
        finally:
            self._ftp = None
            logger.info("FTP disconnected from %s:%s", self._host, self._port)

    def _ensure_connected(self) -> ftplib.FTP:
        """
        Garante que a conexão está aberta.

        Returns:
            Instância ativa de ftplib.FTP.

        Raises:
            RuntimeError: Se a conexão não estiver aberta.
        """
        if self._ftp is None:
            raise RuntimeError(
                "FTP connection not open. Call open() or use context manager."
            )
        return self._ftp

    def list_files(self, path: Optional[str] = None) -> list[str]:
        """
        Lista nomes de arquivos em um diretório remoto.

        Args:
            path: Caminho do diretório. Se None, usa o diretório atual.

        Returns:
            Lista de nomes de arquivos (sem caminho completo).
        """
        ftp = self._ensure_connected()
        target = path or "."
        files = ftp.nlst(target)
        return [f.split("/")[-1] for f in files]

    def get_file(self, remote_path: str) -> BytesIO:
        """
        Baixa um arquivo do servidor FTP.

        Args:
            remote_path: Caminho completo do arquivo no servidor.

        Returns:
            Conteúdo do arquivo como BytesIO.

        Raises:
            RuntimeError: Se a conexão não estiver aberta.
            ftplib.all_errors: Se falhar ao baixar.
        """
        ftp = self._ensure_connected()
        data = bytearray()

        def _collect(chunk: bytes) -> None:
            data.extend(chunk)

        ftp.retrbinary(f"RETR {remote_path}", _collect)
        return BytesIO(data)

    def send_file(self, remote_path: str, content: Union[bytes, BytesIO]) -> None:
        """
        Envia um arquivo para o servidor FTP.

        Args:
            remote_path: Caminho de destino no servidor.
            content: Conteúdo do arquivo em bytes ou BytesIO.

        Raises:
            RuntimeError: Se a conexão não estiver aberta.
            ftplib.all_errors: Se falhar ao enviar.
        """
        ftp = self._ensure_connected()

        if isinstance(content, bytes):
            content = BytesIO(content)

        content.seek(0)
        ftp.storbinary(f"STOR {remote_path}", content)

    def delete_file(self, remote_path: str) -> None:
        """
        Remove um arquivo do servidor FTP.

        Args:
            remote_path: Caminho do arquivo a ser removido.

        Raises:
            RuntimeError: Se a conexão não estiver aberta.
            ftplib.all_errors: Se falhar ao deletar.
        """
        ftp = self._ensure_connected()
        ftp.delete(remote_path)

    def __enter__(self) -> "FTPConnector":
        self.open()
        return self

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        self.close()

