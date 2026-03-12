"""
Mock do GraphQLConnector para a Fidelize Wholesaler.

Retorna dados fake de pedidos sem fazer nenhuma chamada de rede.
Ativado via MOCK_WHOLESALER=true no .env.
"""

from typing import Any, Optional
import re


MOCK_ORDERS: list[dict[str, Any]] = [
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
        "additional_information": "Pedido urgente - MOCK",
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


class MockWholesalerConnector:
    """
    Mock do GraphQLConnector que simula a API Fidelize Wholesaler.

    Interpreta a query GraphQL e retorna dados fake.
    Não faz nenhuma chamada de rede.
    """

    def __init__(self) -> None:
        self._imported: set[int] = set()

    @property
    def base_url(self) -> str:
        return "mock://fidelize-wholesaler"

    @property
    def timeout(self) -> int:
        return 30

    async def execute(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Roteia pela operação detectada na query."""
        q = query.strip().lower()

        if "setorderasimported" in q:
            return self._handle_confirm(query)
        if "orders" in q and "mutation" not in q:
            return self._handle_orders(query)

        return {}

    def _handle_orders(self, query: str) -> dict[str, Any]:
        m = re.search(r'industry_code:\s*"([^"]+)"', query)
        industry = m.group(1) if m else None

        filtered = [
            o for o in MOCK_ORDERS
            if o["order_code"] not in self._imported
            and (industry is None or o["industry_code"] == industry)
        ]

        return {
            "orders": {
                "total": len(filtered),
                "from": 1,
                "to": len(filtered),
                "data": filtered,
            }
        }

    def _handle_confirm(self, query: str) -> dict[str, Any]:
        m = re.search(r'order_code:\s*(\d+)', query)
        if not m:
            return {}

        code = int(m.group(1))
        order = next((o for o in MOCK_ORDERS if o["order_code"] == code), None)
        if not order:
            return {}

        self._imported.add(code)
        return {
            "setOrderAsImported": {
                "id": order["id"],
                "order_code": code,
                "customer_code": order["customer_code"],
                "customer_alternative_code": order.get("customer_alternative_code"),
            }
        }

