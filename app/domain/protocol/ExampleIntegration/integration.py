from typing import Protocol


class ExampleIntegrationProtocol(Protocol):

    def login(self, username: str, password: str) -> str:
        """Realiza o login na integração e retorna um token de autenticação."""
        ...

    def send_data(self, token: str, data: dict) -> bool:
        """Envia dados para a integração usando o token de autenticação."""
        ...
