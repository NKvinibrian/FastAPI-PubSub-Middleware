
import httpx
from app.infrastructure.auth.base_auth_provider import BaseAuthProviderProtocol


class GraphQLAuthProvider(BaseAuthProviderProtocol):

    def __init__(self,
                 url: str,
                 username: str,
                 password: str,
                 method: str = 'POST',
                 username_field: str = 'login',
                 password_field: str = 'password',
                 mutation_name: str = 'createToken',
                 response_token_field: str = 'token'
                 ) -> None:
        """
        username_field / password_field:
          nomes dos argumentos da mutation
        mutation_name:
          nome da mutation de login no schema
        response_token_field:
          nome do campo dentro de createToken { token }
        """
        super().__init__(response_token_field)
        self.url = url
        self.username = username
        self.password = password
        self.method = method.upper()
        self.username_field = username_field
        self.password_field = password_field
        self.mutation_name = mutation_name

    async def build_auth(self) -> httpx.Request:
        """
        Monta um httpx.Request para a mutation GraphQL de login.
        """
        query = f"""
        mutation {self.mutation_name}(
          ${self.username_field}: String!,
          ${self.password_field}: String!
        ) {{
          {self.mutation_name}(
            {self.username_field}: ${self.username_field},
            {self.password_field}: ${self.password_field}
          ) {{
            {self.response_token_field}
          }}
        }}
        """

        payload = {
            "query": query,
            "variables": {
                self.username_field: self.username,
                self.password_field: self.password,
            }
        }

        async with httpx.AsyncClient() as client:
            headers = {
                "Content-Type": "application/json",
            }
            req = client.build_request(
                method=self.method,
                url=self.url,
                headers=headers,
                json=payload
            )
        return req
