from app.domain.protocol.ExampleIntegration.integration import ExampleIntegrationProtocol

class MockExampleIntegrationService(ExampleIntegrationProtocol):

    def login(self, username: str, password: str) -> str:
        return 'Mock Token'

    def send_data(self, token: str, data: dict) -> bool:
        print(f"Mock sending data: {data} with token: {token}")
        return True
