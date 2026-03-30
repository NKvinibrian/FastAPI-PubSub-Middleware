# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start databases (PostgreSQL + MongoDB)
docker-compose up -d

# Run the app
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Install dependencies
uv sync

# Run all tests
pytest

# Run a single test file
pytest app/tests/vans/test_wholesaler_integration.py -v

# Run a single test class
pytest app/tests/vans/test_wholesaler_integration.py::TestMockAuth -v

# Run a single test method
pytest app/tests/vans/test_wholesaler_integration.py::TestMockAuth::test_connector_authenticates_with_mock_server -v -s

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

This is a **VAN (Value-Added Network) integration platform** that fetches supplier orders via external APIs, parses them, and publishes them to GCP Pub/Sub for downstream processing.

### Layered Structure

```
app/
├── api/v1/routes/     # FastAPI endpoints
├── core/              # Config, dependency injection, MongoDB connection
├── domain/            # Business logic: entities, protocols (interfaces), services
├── infrastructure/    # External integrations: DB, Pub/Sub, auth, VAN connectors
├── jobs/              # Background job runners
├── pipelines/         # Order processing pipeline orchestration
└── tests/             # Tests + mock implementations
```

### Key Patterns

**Protocol-based interfaces** — `app/domain/protocol/` defines structural typing protocols (not ABC). Implementations live in `app/infrastructure/`. This makes swapping real vs. mock implementations trivial.

**Dependency injection** — `app/core/dependencies.py` contains factory functions used with FastAPI's `Depends()`. The `MOCK_WHOLESALER` and `MOCK_PUBSUB` env vars switch between real and mock implementations.

**Generic VAN Pipeline** — `app/pipelines/vans/van_pipeline.py` implements a reusable Fetch → Parse → Publish flow. Each VAN plugs in its own fetcher, parser, and loop function (which controls what context values to iterate, e.g. industry codes).

**Dual database** — PostgreSQL (SQLAlchemy, synchronous) stores integration configs, auth credentials, and users. MongoDB (Motor, async) stores request logs and integration audit events.

**Dual logging** — HTTP request logging via middleware → MongoDB. Business-process logging (fetch/parse/publish stages) via `IntegrationLogger` → MongoDB + PostgreSQL.

### Order Processing Flow

1. **Fetch** — VAN-specific fetcher calls external API (e.g. Fidelize GraphQL)
2. **Parse** — Converts raw response to `PrePedidoSchema`
3. **Publish** — One Pub/Sub message per order
4. **Confirm** — Datasul subscriber marks orders as imported in the VAN

### Configuration

Settings are loaded from `.env` via Pydantic `BaseSettings` in `app/core/config.py` and cached with `@lru_cache`.

Key env vars:
- `ENV` — `dev` or `prod`
- `MOCK_WHOLESALER` / `MOCK_PUBSUB` — `true` to use in-memory mocks instead of real GCP/VAN APIs
- `GCP_PROJECT_ID`, `GCP_CREDENTIALS_PATH` — GCP Pub/Sub access
- `MONGO_URI`, `MONGO_DB_NAME` — MongoDB
- `POSTGRES_HOST/PORT/USER/PASSWORD/DB` — PostgreSQL
- `SECRET_KEY` — JWT signing
- `BINARY_DECODE` — encoding for binary data (default: `latin1`)

### Testing

Tests use `pytest-asyncio` for async tests. Mocks are in `app/tests/mocks/`. FastAPI dependency overrides (`app.dependency_overrides`) are used to inject mock implementations. Tests rely on mock servers built with `httpx.ASGITransport` — no real network calls occur.
