from typing import Protocol


class DatasulProtocol(Protocol):
    """
    Protocolo para integrações externas que requerem autenticação.

    Define a interface padrão para serviços de integração que seguem
    o padrão de login com credenciais seguido de operações autenticadas.
    """

    def login(self, username: str, password: str) -> str:
        """
        Realiza o login na integração e retorna um token de autenticação.

        Args:
            username: Nome de usuário para autenticação
            password: Senha para autenticação

        Returns:
            str: Token de autenticação para uso em operações subsequentes
        """
        ...

    def send_pre_pedido(self, token: str, data: dict) -> bool:
        """
        Envia dados para a integração usando o token de autenticação.

        Args:
            token: Token de autenticação obtido no login
            data: Dicionário com os dados a serem enviados

        Returns:
            bool: True se o envio foi bem-sucedido, False caso contrário
        """
        ...
