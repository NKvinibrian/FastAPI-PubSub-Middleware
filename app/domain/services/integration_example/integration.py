from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol


class ExampleIntegrationService(ExampleIntegrationProtocol):

    def login(self, username: str, password: str) -> str:
        return 'Teste nao mock Token'

    def send_data(self, token: str, data: dict) -> bool:
        print(f"Sending data: {data} with token: {token}")
        return True

