from app.domain.protocol.integrations.repository import IntegrationsRepositoryProtocol
from app.domain.protocol.auth.auth_provider import AuthProviderProtocol
from app.infrastructure.auth.context import AuthContext
from app.infrastructure.auth.basic_auth import BasicAuthProvider
from app.infrastructure.auth.body_auth import BodyAuthProvider
from app.infrastructure.auth.graphql_auth import GraphQLAuthProvider
from app.infrastructure.auth.bearer import BearerAuthProvider


_AUTH_TYPE_MAP = {
    "basic": "_build_basic",
    "body": "_build_body",
    "graphql": "_build_graphql",
    "bearer": "_build_bearer",
    "token": "_build_bearer",
}


class AuthLoader:

    def __init__(self, auth_repository: IntegrationsRepositoryProtocol):
        self.auth_repository = auth_repository

    def load(self, integration_name: str) -> AuthContext:
        integration_data = self.auth_repository.get_by_name_with_auth(name=integration_name)

        if not integration_data:
            raise ValueError(f"Integration with name '{integration_name}' not found.")

        auth_provider = self._build_auth_provider(integration_data)

        return AuthContext(
            integration_name=integration_name,
            provider=auth_provider,
            base_url=integration_data.base_url,
            timeout=integration_data.timeout,
            type_api=integration_data.type_api
        )

    def _build_auth_provider(self, integration_data) -> AuthProviderProtocol:
        auth = integration_data.auth
        auth_type = auth.auth_type.lower()

        builder_name = _AUTH_TYPE_MAP.get(auth_type)
        if builder_name is None:
            raise ValueError(
                f"Unsupported auth_type '{auth.auth_type}'. "
                f"Supported types: {list(_AUTH_TYPE_MAP.keys())}"
            )

        return getattr(self, builder_name)(integration_data, auth)

    @staticmethod
    def _build_basic(integration_data, auth) -> BasicAuthProvider:
        return BasicAuthProvider(
            url=integration_data.base_url if auth.auth_endpoint is None else f'{integration_data.base_url}{auth.auth_endpoint}',
            username=auth.username,
            password=auth.password,
            method=auth.mutation or "POST",
            response_token_field=auth.token_field or "token",
        )

    @staticmethod
    def _build_body(integration_data, auth) -> BodyAuthProvider:
        return BodyAuthProvider(
            url=integration_data.base_url if auth.auth_endpoint is None else f'{integration_data.base_url}{auth.auth_endpoint}',
            username=auth.username,
            password=auth.password,
            username_field="username",
            password_field="password",
            method=auth.mutation or "POST",
            type_body=auth.response_type or "json",
            response_token_field=auth.token_field or "token",
            custom_headers=auth.headers or {},
        )

    @staticmethod
    def _build_graphql(integration_data, auth) -> GraphQLAuthProvider:
        return GraphQLAuthProvider(
            url=integration_data.base_url if auth.auth_endpoint is None else f'{integration_data.base_url}{auth.auth_endpoint}',
            username=auth.username,
            password=auth.password,
            method=auth.mutation or "POST",
            response_token_field=auth.token_field or "token",
        )

    @staticmethod
    def _build_bearer(auth) -> BearerAuthProvider:
        return BearerAuthProvider(token=auth.token)
