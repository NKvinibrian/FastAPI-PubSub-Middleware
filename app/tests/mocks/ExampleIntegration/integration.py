"""
Módulo de mock para integração de exemplo.

Este módulo fornece uma implementação mock do serviço de integração
para uso em testes automatizados.

Classes:
    MockExampleIntegrationService: Mock do serviço de integração
"""

from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol


class MockExampleIntegrationService(ExampleIntegrationProtocol):
    """
    Mock do serviço de integração externa para testes.

    Esta classe simula o comportamento do serviço de integração real
    sem realizar chamadas externas, permitindo testes isolados e rápidos.
    """

    def login(self, username: str, password: str) -> str:
        """
        Simula o login e retorna um token mock.

        Args:
            username: Nome de usuário (ignorado no mock)
            password: Senha (ignorada no mock)

        Returns:
            str: Token de autenticação fictício para testes
        """
        return 'Mock Token'

    def send_data(self, token: str, data: dict) -> bool:
        """
        Simula o envio de dados.

        Args:
            token: Token de autenticação (validação não realizada no mock)
            data: Dados a serem enviados

        Returns:
            bool: Sempre retorna True para simular sucesso
        """
        print(f"Mock sending data: {data} with token: {token}")
        return True
