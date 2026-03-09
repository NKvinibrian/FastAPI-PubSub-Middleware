import httpx
import base64
from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol


class BasicAuthProvider(BaseAuthProviderProtocol):

    def __init__(self, url: str, username: str, password: str, method:str = 'POST', response_token_field:str = 'token') -> None:
        super().__init__(response_token_field)
        self.url = url
        self.username = username
        self.password = password
        self.method = method.upper()

    async def build_auth(self, headers:dict = None):
        async with httpx.AsyncClient() as client:
            credentials = f"{self.username}:{self.password}".encode("utf-8")
            token = base64.b64encode(credentials).decode("utf-8")

            if headers:
                headers["Authorization"] = f"Basic {token}"
            else:
                headers = {
                    "Authorization": f"Basic {token}"
                }
            return client.build_request(self.method, self.url, headers=headers)
