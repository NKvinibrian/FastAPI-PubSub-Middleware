import httpx
import re
from app.domain.protocol.auth.auth_provider import AuthProviderProtocol


class BaseAuthProviderProtocol(AuthProviderProtocol):

    def __init__(self, response_token_field: str):
        self.response_token_field = response_token_field

    def _find_token(self, dado):
        stack = [dado]

        while stack:
            atual = stack.pop()

            if isinstance(atual, dict):
                for chave, valor in atual.items():
                    if chave.lower() == self.response_token_field:
                        return valor
                    stack.append(valor)

            elif isinstance(atual, list):
                stack.extend(atual)

        return None

    def build_token_req(self, response: httpx.Response) -> str:

        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            dados = response.json()
            token = self._find_token(dados)

        elif "text/html" in content_type:
            dados = response.json()
            token = self._find_token(dados)

        elif "application/xml" in content_type or "text/xml" in content_type:
            padrao = r"<token>(.*?)</token>"
            match = re.search(padrao, response.text)

            token = match.group(1).strip() if match else None

        else:
            token = response.content

        if token is None:
            raise ValueError("Token not found")

        return f"Bearer {token}"
