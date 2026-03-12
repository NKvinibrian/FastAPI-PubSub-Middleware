import httpx
from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol


class BearerAuthProvider(BaseAuthProviderProtocol):

    def __init__(self, token: str, response_token_field: str = "token") -> None:
        super().__init__(response_token_field)
        self.token = token

    async def build_auth(self, headers: dict = None) -> dict:
        auth_headers = headers.copy() if headers else {}
        auth_headers["Authorization"] = f"Bearer {self.token}"
        return auth_headers

