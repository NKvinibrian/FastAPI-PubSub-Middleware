"""
Mock Server da API GraphQL Fidelize Funcional Wholesaler.

Simula as operações do manual Wholesaler v2.2:
- createToken (autenticação)
- orders (consulta pedidos)
- setOrderAsImported (confirma importação)
- createResponse / createInvoice / createCancellation (observer mutations)

Roda como app ASGI (FastAPI) — pode ser usado tanto via
httpx.ASGITransport (testes in-process) quanto via uvicorn
(testes manuais na porta local).

Dados de pedidos são configuráveis via reset_orders():
    reset_orders()               → restaura _DEFAULT_ORDERS (order codes fixos para testes)
    reset_orders(count=N)        → gera N pedidos aleatórios
    reset_orders(count=N, seed=X)→ gera N pedidos aleatórios reproduzíveis
    reset_orders(orders=[...])   → usa lista customizada
"""

import random
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

_INDUSTRY_CODES = ["SAN", "RCH", "FAB", "AZT", "MSD", "PFZ", "NOV", "ELI"]
_PAYMENT_TERMS = ["30", "30/60", "60", "30/60/90", None]
_COMMERCIAL_CONDITIONS = ["CC001", "CC002", "CC003", None]


def _rand_cnpj(rng: random.Random) -> str:
    """Gera CNPJ fictício (14 dígitos sem formatação)."""
    return "".join(str(rng.randint(0, 9)) for _ in range(14))


def _rand_ean(rng: random.Random) -> str:
    """Gera EAN-13 fictício."""
    return str(rng.randint(1_000_000_000_000, 9_999_999_999_999))


def generate_random_orders(count: int = 3, seed: int | None = None) -> list[dict[str, Any]]:
    """
    Gera uma lista de pedidos fictícios no formato da API Fidelize.

    Args:
        count: Quantidade de pedidos a gerar (padrão 3).
        seed:  Semente para reprodutibilidade (None = aleatório a cada chamada).

    Returns:
        Lista de dicts compatível com o formato de _DEFAULT_ORDERS.
    """
    rng = random.Random(seed)
    base_code = rng.randint(10_000, 90_000)
    wholesaler_cnpj = _rand_cnpj(rng)
    wholesaler_branch = _rand_cnpj(rng)

    orders = []
    for i in range(count):
        order_code = base_code + i
        industry_code = rng.choice(_INDUSTRY_CODES)
        customer_code = _rand_cnpj(rng)

        num_products = rng.randint(1, 4)
        products = []
        for _ in range(num_products):
            gross = round(rng.uniform(5.0, 500.0), 2)
            disc = round(rng.uniform(0, 20), 1)
            net = round(gross * (1 - disc / 100), 2)
            products.append({
                "ean": _rand_ean(rng),
                "gross_value": gross,
                "amount": rng.randint(1, 50),
                "discount_percentage": disc,
                "net_value": net,
                "monitored": rng.random() < 0.2,
                "payment_term": rng.choice(_PAYMENT_TERMS),
            })

        orders.append({
            "id": str(rng.randint(90_000, 999_999)),
            "order_code": order_code,
            "status": "ORDER_NOT_IMPORTED",
            "tradetools_created_at": "2026-03-30T10:00:00Z",
            "notification_obs": None,
            "notification_status": "SENT",
            "industry_code": industry_code,
            "customer_code": customer_code,
            "customer_alternative_code": None,
            "customer_email": None,
            "customer_code_type": "CNPJ",
            "distribution_center_code": f"CD0{i + 1}",
            "order_payment_term": rng.choice(_PAYMENT_TERMS) or "30",
            "commercial_condition_code": rng.choice(_COMMERCIAL_CONDITIONS),
            "customer_order_code": f"PED-{order_code}",
            "destination_customer": None,
            "profit_share_margin": None,
            "is_free_good_discount": False,
            "recalculates_discount": False,
            "indicator": None,
            "salesman_code": f"VND-{rng.randint(1, 99):03d}",
            "scheduled_delivery_order": rng.random() < 0.15,
            "sends_either_value_or_discount": False,
            "sends_only_discount": False,
            "additional_information": None,
            "wholesaler_branch_code": wholesaler_branch,
            "wholesaler_code": wholesaler_cnpj,
            "products": products,
        })

    return orders


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


def reset_orders(
    orders: list[dict[str, Any]] | None = None,
    count: int | None = None,
    seed: int | None = None,
) -> None:
    """
    Reseta o estado do mock.

    Prioridade:
        1. `orders` → usa a lista fornecida
        2. `count`  → gera `count` pedidos aleatórios (reproduzível com `seed`)
        3. padrão   → restaura _DEFAULT_ORDERS (order codes fixos 5001/5002/5003)

    Exemplos:
        reset_orders()               # 5001, 5002, 5003 (para testes existentes)
        reset_orders(count=10)       # 10 pedidos aleatórios
        reset_orders(count=5, seed=42) # 5 pedidos reproduzíveis
        reset_orders(orders=[...])   # lista customizada
    """
    global _orders, _imported_order_codes
    if orders is not None:
        _orders = [dict(o) for o in orders]
    elif count is not None:
        _orders = generate_random_orders(count=count, seed=seed)
    else:
        _orders = [dict(o) for o in _DEFAULT_ORDERS]
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
    if "createresponse" in q:
        return "createResponse"
    if "createinvoice" in q:
        return "createInvoice"
    if "createcancellation" in q:
        return "createCancellation"
    if "orders" in q and "mutation" not in q:
        return "orders"
    return "unknown"


def _handle_create_response(query: str) -> dict:
    """Simula createResponse — confirma retorno de pedido aceito ou rejeitado."""
    m = re.search(r'order_code:\s*(\d+)', query)
    order_code = int(m.group(1)) if m else 0
    return {
        "data": {
            "createResponse": {
                "id": str(order_code),
                "content": "response created",
                "imported_at": "2026-03-30T10:00:00Z",
                "outcome": "SUCCESS",
            }
        }
    }


def _handle_create_invoice(query: str) -> dict:
    """Simula createInvoice — confirma envio de nota fiscal."""
    m = re.search(r'order_code:\s*(\d+)', query)
    order_code = int(m.group(1)) if m else 0
    return {
        "data": {
            "createInvoice": {
                "id": str(order_code),
                "content": "invoice created",
                "imported_at": "2026-03-30T10:00:00Z",
                "outcome": "SUCCESS",
            }
        }
    }


def _handle_create_cancellation(query: str) -> dict:
    """Simula createCancellation — confirma cancelamento de pedido."""
    m = re.search(r'order_code:\s*(\d+)', query)
    order_code = int(m.group(1)) if m else 0
    return {
        "data": {
            "createCancellation": {
                "id": str(order_code),
                "content": "cancellation created",
                "imported_at": "2026-03-30T10:00:00Z",
                "outcome": "SUCCESS",
            }
        }
    }


@app.post("/graphql")
@app.post("/graphql/")
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
    elif operation == "createResponse":
        result = _handle_create_response(query)
    elif operation == "createInvoice":
        result = _handle_create_invoice(query)
    elif operation == "createCancellation":
        result = _handle_create_cancellation(query)
    else:
        result = _graphql_error(f"Unknown operation in query", "BAD_REQUEST")

    return JSONResponse(content=result)


@app.post("/reset")
async def reset_endpoint() -> JSONResponse:
    """Endpoint auxiliar para resetar o estado do mock entre testes."""
    reset_orders()
    return JSONResponse(content={"status": "reset"})

