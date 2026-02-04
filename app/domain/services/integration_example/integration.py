"""
Módulo de serviço de integração de exemplo.

Este módulo implementa o serviço de integração externa seguindo
o ExampleIntegrationProtocol.

Classes:
    ExampleIntegrationService: Implementação do serviço de integração
"""

from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol


class ExampleIntegrationService(ExampleIntegrationProtocol):
    """
    Serviço de integração externa de exemplo.

    Esta classe implementa o protocolo de integração com uma API externa
    fictícia para demonstração.
    """

    def login(self, username: str, password: str) -> str:
        """
        Realiza o login e retorna um token.

        Args:
            username: Nome de usuário
            password: Senha

        Returns:
            str: Token de autenticação (mock para testes)
        """
        return 'Teste nao mock Token'

    def send_data(self, token: str, data: dict) -> bool:
        """
        Envia dados usando o token de autenticação.

        Args:
            token: Token de autenticação
            data: Dados a serem enviados

        Returns:
            bool: True indicando sucesso no envio
        """
        print(f"Sending data: {data} with token: {token}")
        return True

