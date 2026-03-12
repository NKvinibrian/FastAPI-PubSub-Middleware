"""
Testes do AuthLoader.

Cobre:
  1. Criação do contexto para cada auth_type suportado
     (basic, body, graphql, bearer, token)
  2. Tipo correto de AuthProvider instanciado
  3. Parâmetros repassados corretamente ao provider
  4. Erro ao receber auth_type desconhecido
  5. Erro ao integration não encontrada no repositório
  6. Fluxo completo: loader → AuthContext → build_auth()
"""

import pytest

from app.infrastructure.auth.loader import AuthLoader
from app.infrastructure.auth.context import AuthContext
from app.infrastructure.auth.basic_auth import BasicAuthProvider
from app.infrastructure.auth.body_auth import BodyAuthProvider
from app.infrastructure.auth.graphql_auth import GraphQLAuthProvider
from app.infrastructure.auth.bearer import BearerAuthProvider

from app.tests.mocks.auth.integration_repository import (
    MockIntegrationsRepository,
    make_basic_auth,
    make_body_auth,
    make_graphql_auth,
    make_bearer_auth,
    make_token_auth,
    _base_auth,
)

INTEGRATION_NAME = "test-integration"


# ── helpers ──────────────────────────────────────────────────────────────────

def _loader(auth):
    repo = MockIntegrationsRepository(auth=auth)
    return AuthLoader(auth_repository=repo)


# ── 1. AuthContext é sempre retornado ─────────────────────────────────────────

class TestAuthLoaderReturnsAuthContext:

    def test_returns_auth_context_for_basic(self):
        ctx = _loader(make_basic_auth()).load(INTEGRATION_NAME)
        assert isinstance(ctx, AuthContext)

    def test_context_carries_integration_name(self):
        ctx = _loader(make_basic_auth()).load(INTEGRATION_NAME)
        assert ctx.integration_name == INTEGRATION_NAME

    def test_context_provider_is_not_none(self):
        ctx = _loader(make_bearer_auth()).load(INTEGRATION_NAME)
        assert ctx.provider is not None


# ── 2. Provider correto por auth_type ────────────────────────────────────────

class TestAuthLoaderBuildsCorrectProvider:

    def test_basic_auth_type_builds_basic_provider(self):
        ctx = _loader(make_basic_auth()).load(INTEGRATION_NAME)
        assert isinstance(ctx.provider, BasicAuthProvider)

    def test_body_auth_type_builds_body_provider(self):
        ctx = _loader(make_body_auth()).load(INTEGRATION_NAME)
        assert isinstance(ctx.provider, BodyAuthProvider)

    def test_graphql_auth_type_builds_graphql_provider(self):
        ctx = _loader(make_graphql_auth()).load(INTEGRATION_NAME)
        assert isinstance(ctx.provider, GraphQLAuthProvider)

    def test_bearer_auth_type_builds_bearer_provider(self):
        ctx = _loader(make_bearer_auth()).load(INTEGRATION_NAME)
        assert isinstance(ctx.provider, BearerAuthProvider)

    def test_token_alias_also_builds_bearer_provider(self):
        ctx = _loader(make_token_auth()).load(INTEGRATION_NAME)
        assert isinstance(ctx.provider, BearerAuthProvider)

    def test_auth_type_is_case_insensitive(self):
        auth = _base_auth(auth_type="BASIC")
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert isinstance(ctx.provider, BasicAuthProvider)


# ── 3. Parâmetros repassados corretamente ────────────────────────────────────

class TestAuthLoaderProviderParameters:

    def test_basic_provider_receives_correct_url(self):
        auth = make_basic_auth()
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.url == auth.auth_endpoint

    def test_basic_provider_receives_correct_credentials(self):
        auth = make_basic_auth()
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.username == auth.username
        assert ctx.provider.password == auth.password

    def test_basic_provider_token_field_fallback(self):
        auth = _base_auth(auth_type="basic", token_field=None)
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.response_token_field == "token"

    def test_basic_provider_token_field_custom(self):
        auth = _base_auth(auth_type="basic", token_field="jwt")
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.response_token_field == "jwt"

    def test_body_provider_receives_correct_url(self):
        auth = make_body_auth()
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.url == auth.auth_endpoint

    def test_body_provider_receives_custom_headers(self):
        auth = _base_auth(auth_type="body", headers={"X-App": "test"})
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.custom_headers == {"X-App": "test"}

    def test_body_provider_headers_default_to_empty_dict(self):
        auth = _base_auth(auth_type="body", headers=None)
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.custom_headers == {}

    def test_graphql_provider_receives_correct_url(self):
        auth = make_graphql_auth()
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.url == auth.auth_endpoint

    def test_graphql_mutation_fallback_to_post(self):
        auth = _base_auth(auth_type="graphql", mutation=None)
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.method == "POST"

    def test_bearer_provider_receives_token(self):
        auth = make_bearer_auth()
        ctx = _loader(auth).load(INTEGRATION_NAME)
        assert ctx.provider.token == "my-static-token"


# ── 4. Erros esperados ───────────────────────────────────────────────────────

class TestAuthLoaderErrors:

    def test_raises_value_error_for_unknown_auth_type(self):
        auth = _base_auth(auth_type="ftp")
        with pytest.raises(ValueError, match="Unsupported auth_type"):
            _loader(auth).load(INTEGRATION_NAME)

    def test_raises_value_error_when_integration_not_found(self):
        repo = MockIntegrationsRepository(auth=None)
        loader = AuthLoader(auth_repository=repo)
        with pytest.raises(ValueError, match="not found"):
            loader.load("nonexistent-integration")

    def test_error_message_includes_auth_type_name(self):
        auth = _base_auth(auth_type="unknown_type")
        with pytest.raises(ValueError, match="unknown_type"):
            _loader(auth).load(INTEGRATION_NAME)


# ── 5. Fluxo completo: loader → context → build_auth() ───────────────────────

class TestAuthLoaderEndToEndFlow:

    @pytest.mark.asyncio
    async def test_bearer_build_auth_returns_authorization_header(self):
        ctx = _loader(make_bearer_auth()).load(INTEGRATION_NAME)
        headers = await ctx.provider.build_auth()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my-static-token"

    @pytest.mark.asyncio
    async def test_bearer_build_auth_merges_existing_headers(self):
        ctx = _loader(make_bearer_auth()).load(INTEGRATION_NAME)
        headers = await ctx.provider.build_auth(headers={"X-Custom": "value"})
        assert headers["X-Custom"] == "value"
        assert headers["Authorization"] == "Bearer my-static-token"

    @pytest.mark.asyncio
    async def test_basic_build_auth_returns_request(self):
        ctx = _loader(make_basic_auth()).load(INTEGRATION_NAME)
        result = await ctx.provider.build_auth()
        # BasicAuthProvider retorna um httpx.Request
        import httpx
        assert isinstance(result, httpx.Request)
        assert "Authorization" in result.headers
        assert result.headers["Authorization"].startswith("Basic ")

    @pytest.mark.asyncio
    async def test_body_build_auth_returns_request_with_json_content_type(self):
        ctx = _loader(make_body_auth()).load(INTEGRATION_NAME)
        result = await ctx.provider.build_auth()
        import httpx
        assert isinstance(result, httpx.Request)
        assert "application/json" in result.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_graphql_build_auth_returns_request_with_query(self):
        ctx = _loader(make_graphql_auth()).load(INTEGRATION_NAME)
        result = await ctx.provider.build_auth()
        import httpx
        assert isinstance(result, httpx.Request)
        body = result.content.decode()
        assert "mutation" in body

