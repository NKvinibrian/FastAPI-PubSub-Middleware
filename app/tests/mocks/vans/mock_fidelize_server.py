"""
Mock Server da API GraphQL Fidelize Funcional Wholesaler.

Simula as operações do manual Wholesaler v2.2:
- createToken (autenticação)
- orders (consulta pedidos)
- setOrderAsImported (confirma importação)

Roda como app ASGI (FastAPI) — pode ser usado tanto via
httpx.ASGITransport (testes in-process) quanto via uvicorn
(testes manuais na porta local).

Dados de pedidos são configuráveis via MOCK_ORDERS.
"""

import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock Fidelize Wholesaler GraphQL")

# ══════════════════════════════════════════════════════════════════════════════
#  Configuração do mock
# ══════════════════════════════════════════════════════════════════════════════

MOCK_TOKEN = "mock-jwt-token-fidelize-wholesaler-2026"
MOCK_USERNAME = "test.distribuidor"
MOCK_PASSWORD = "test123"

# Pedidos disponíveis — resetáveis via reset_orders()
_DEFAULT_ORDERS: list[dict[str, Any]] = [
    {
        "id": "98001",
        "order_code": 5001,
        "status": "ORDER_NOT_IMPORTED",
        "tradetools_created_at": "2026-03-10T14:30:00Z",
        "notification_obs": None,
        "notification_status": "SENT",
        "industry_code": "SAN",
        "customer_code": "12345678000100",
        "customer_alternative_code": "ALT-001",
        "customer_email": "cliente@test.com",
        "customer_code_type": "CNPJ",
        "distribution_center_code": "CD01",
        "order_payment_term": "30/60",
        "commercial_condition_code": "CC001",
        "customer_order_code": "PED-001",
        "destination_customer": None,
        "profit_share_margin": None,
        "is_free_good_discount": False,
        "recalculates_discount": False,
        "indicator": None,
        "salesman_code": "VND-001",
        "scheduled_delivery_order": False,
        "sends_either_value_or_discount": False,
        "sends_only_discount": False,
        "additional_information": "Pedido urgente",
        "wholesaler_branch_code": "98765432000100",
        "wholesaler_code": "98765432000199",
        "products": [
            {
                "ean": "7899640800117",
                "gross_value": 32.98,
                "amount": 3,
                "discount_percentage": 10.0,
                "net_value": 29.69,
                "monitored": False,
                "payment_term": "30",
            },
            {
                "ean": "7891058003203",
                "gross_value": 15.50,
                "amount": 5,
                "discount_percentage": 5.0,
                "net_value": 14.73,
                "monitored": True,
                "payment_term": "30",
            },
        ],
    },
    {
        "id": "98002",
        "order_code": 5002,
        "status": "ORDER_NOT_IMPORTED",
        "tradetools_created_at": "2026-03-10T15:00:00Z",
        "notification_obs": "Segunda entrega",
        "notification_status": "SENT",
        "industry_code": "SAN",
        "customer_code": "11222333000144",
        "customer_alternative_code": None,
        "customer_email": None,
        "customer_code_type": "CNPJ",
        "distribution_center_code": "CD02",
        "order_payment_term": "30",
        "commercial_condition_code": None,
        "customer_order_code": "PED-002",
        "destination_customer": None,
        "profit_share_margin": None,
        "is_free_good_discount": False,
        "recalculates_discount": False,
        "indicator": None,
        "salesman_code": None,
        "scheduled_delivery_order": True,
        "sends_either_value_or_discount": False,
        "sends_only_discount": False,
        "additional_information": None,
        "wholesaler_branch_code": None,
        "wholesaler_code": "98765432000199",
        "products": [
            {
                "ean": "7896226503288",
                "gross_value": 8.00,
                "amount": 10,
                "discount_percentage": 0.0,
                "net_value": 8.00,
                "monitored": False,
                "payment_term": None,
            },
        ],
    },
    {
        "id": "98003",
        "order_code": 5003,
        "status": "ORDER_NOT_IMPORTED",
        "tradetools_created_at": "2026-03-10T16:00:00Z",
        "notification_obs": None,
        "notification_status": "SENT",
        "industry_code": "RCH",
        "customer_code": "99988877000166",
        "customer_alternative_code": "ALT-003",
        "customer_email": "rch@test.com",
        "customer_code_type": "CNPJ",
        "distribution_center_code": "CD01",
        "order_payment_term": "60",
        "commercial_condition_code": "CC002",
        "customer_order_code": "PED-003",
        "destination_customer": None,
        "profit_share_margin": None,
        "is_free_good_discount": False,
        "recalculates_discount": False,
        "indicator": None,
        "salesman_code": "VND-002",
        "scheduled_delivery_order": False,
        "sends_either_value_or_discount": False,
        "sends_only_discount": False,
        "additional_information": None,
        "wholesaler_branch_code": "98765432000100",
        "wholesaler_code": "98765432000199",
        "products": [
            {
                "ean": "7891234567890",
                "gross_value": 25.00,
                "amount": 2,
                "discount_percentage": 15.0,
                "net_value": 21.25,
                "monitored": True,
                "payment_term": "60",
            },
        ],
    },
]

# Estado mutável do mock
_orders: list[dict[str, Any]] = []
_imported_order_codes: set[int] = set()


def reset_orders(orders: list[dict[str, Any]] | None = None) -> None:
    """Reseta o estado do mock para o padrão ou com dados customizados."""
    global _orders, _imported_order_codes
    _orders = [dict(o) for o in (orders or _DEFAULT_ORDERS)]
    _imported_order_codes = set()


# Inicializa com dados padrão
reset_orders()


# ══════════════════════════════════════════════════════════════════════════════
#  GraphQL request handler
# ══════════════════════════════════════════════════════════════════════════════

def _graphql_error(message: str, code: str = "INTERNAL_ERROR") -> dict:
    return {"data": None, "errors": [{"message": message, "code": code}]}


def _handle_create_token(query: str, variables: dict | None) -> dict:
    """Simula createToken — valida credenciais e retorna JWT."""
    login = None
    password = None

    # Tenta extrair das variables primeiro
    if variables:
        login = variables.get("login") or variables.get("username")
        password = variables.get("password")

    # Fallback: extrai inline da query
    if not login:
        m = re.search(r'login:\s*"([^"]+)"', query)
        if m:
            login = m.group(1)
    if not password:
        m = re.search(r'password:\s*"([^"]+)"', query)
        if m:
            password = m.group(1)

    if login == MOCK_USERNAME and password == MOCK_PASSWORD:
        return {"data": {"createToken": {"token": MOCK_TOKEN}}}

    return _graphql_error("Invalid credentials", "UNAUTHENTICATED")


def _handle_orders(query: str) -> dict:
    """Simula query orders — filtra por industry_code e imported status."""
    # Extrai industry_code da query
    m = re.search(r'industry_code:\s*"([^"]+)"', query)
    industry_code = m.group(1) if m else None

    # Filtra pedidos não importados
    filtered = [
        o for o in _orders
        if o["order_code"] not in _imported_order_codes
        and (industry_code is None or o.get("industry_code") == industry_code)
    ]

    return {
        "data": {
            "orders": {
                "total": len(filtered),
                "from": 1,
                "to": len(filtered),
                "data": filtered,
            }
        }
    }


def _handle_set_order_as_imported(query: str) -> dict:
    """Simula setOrderAsImported — marca pedido e retorna dados."""
    m = re.search(r'order_code:\s*(\d+)', query)
    if not m:
        return _graphql_error("order_code is required", "VALIDATION_ERROR")

    order_code = int(m.group(1))

    # Encontra o pedido
    order = next((o for o in _orders if o["order_code"] == order_code), None)
    if not order:
        return _graphql_error(f"Order {order_code} not found", "NOT_FOUND")

    _imported_order_codes.add(order_code)

    return {
        "data": {
            "setOrderAsImported": {
                "id": order["id"],
                "order_code": order_code,
                "customer_code": order.get("customer_code"),
                "customer_alternative_code": order.get("customer_alternative_code"),
            }
        }
    }


def _detect_operation(query: str) -> str:
    """Detecta a operação GraphQL pela query string."""
    q = query.strip().lower()
    if "createtoken" in q:
        return "createToken"
    if "setorderasimported" in q:
        return "setOrderAsImported"
    if "orders" in q and "mutation" not in q:
        return "orders"
    return "unknown"


@app.post("/graphql")
async def graphql_endpoint(request: Request) -> JSONResponse:
    """Endpoint GraphQL único — roteia pela operação detectada na query."""
    body = await request.json()
    query = body.get("query", "")
    variables = body.get("variables")

    # Auth check (exceto createToken)
    operation = _detect_operation(query)

    if operation != "createToken":
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {MOCK_TOKEN}":
            return JSONResponse(
                status_code=200,
                content=_graphql_error("Unauthorized. Invalid token.", "UNAUTHENTICATED"),
            )

    if operation == "createToken":
        result = _handle_create_token(query, variables)
    elif operation == "orders":
        result = _handle_orders(query)
    elif operation == "setOrderAsImported":
        result = _handle_set_order_as_imported(query)
    else:
        result = _graphql_error(f"Unknown operation in query", "BAD_REQUEST")

    return JSONResponse(content=result)


@app.post("/reset")
async def reset_endpoint() -> JSONResponse:
    """Endpoint auxiliar para resetar o estado do mock entre testes."""
    reset_orders()
    return JSONResponse(content={"status": "reset"})

