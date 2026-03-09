from urllib.parse import urlencode
import httpx
from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol


class BodyAuthProvider(BaseAuthProviderProtocol):

    def __init__(self,
                 url: str,
                 username: str,
                 password: str,
                 username_field: str,
                 password_field: str,
                 method:str = 'POST',
                 type_body: str = 'json',
                 response_token_field: str = 'token',
                 custom_headers: dict | None = None
                 ) -> None:

        super().__init__(response_token_field)
        self.url = url
        self.username = username
        self.password = password
        self.method = method.upper()
        self.type_body = type_body
        self.username_field = username_field
        self.password_field = password_field
        self.custom_headers = custom_headers or {}


    async def build_auth(self) -> httpx.Request:
        """
        Monta um httpx.Request via client.build_request()
        com body conforme `self.type_body`.
        """

        payload = {
            self.username_field: self.username,
            self.password_field: self.password,
        }

        # abre o client para usar build_request
        async with httpx.AsyncClient() as client:
            headers = {**self.custom_headers}

            if self.type_body == 'json':
                headers.setdefault('Content-Type', 'application/json')
                req = client.build_request(
                    method=self.method,
                    url=self.url,
                    headers=headers,
                    json=payload
                )

            elif self.type_body in ('form', 'form-urlencoded'):
                headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                req = client.build_request(
                    method=self.method,
                    url=self.url,
                    headers=headers,
                    data=payload
                )

            elif self.type_body == 'multipart':
                # cria multipart/form-data
                files = {k: (None, str(v)) for k, v in payload.items()}
                req = client.build_request(
                    method=self.method,
                    url=self.url,
                    headers=headers,
                    files=files
                )

            else:
                # fallback urlencoded manual
                body_text = urlencode(payload)
                headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
                req = client.build_request(
                    method=self.method,
                    url=self.url,
                    headers=headers,
                    content=body_text
                )

            return req
