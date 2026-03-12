"""
Mocks para testes do fluxo completo de VANs.

Contém mocks in-memory para:
- LogPrePedidosVansRepository
- IntegrationLogRepository
- GraphQLFetcher (simula respostas GraphQL)
- PubSubPublisher (simula publicação)
"""

from typing import Any, Optional, Union
from uuid import UUID
from copy import deepcopy

from app.domain.entities.logs.vans import LogPrePedidosVansEntity
from app.domain.entities.logs.integrations import IntegrationLogEntity


# ═══════════════════════════════════════════════════════════════════════
#  Mock: LogPrePedidosVansRepository (in-memory)
# ═══════════════════════════════════════════════════════════════════════

class MockLogPrePedidosVansRepository:
    """
    Mock in-memory do repositório de LogPrePedidosVans.
    Armazena logs numa lista e auto-incrementa o id.
    """

    def __init__(self) -> None:
        self._logs: list[LogPrePedidosVansEntity] = []
        self._next_id: int = 1

    def get_all(self) -> list[LogPrePedidosVansEntity]:
        return list(self._logs)

    def get_by_id(self, log_id: int) -> Optional[LogPrePedidosVansEntity]:
        return next((l for l in self._logs if l.id == log_id), None)

    def get_by_pedido_van_id(self, pedido_van_id: str) -> list[LogPrePedidosVansEntity]:
        return [l for l in self._logs if l.pedido_van_id == pedido_van_id]

    def get_by_message_id(self, message_id: int) -> Optional[LogPrePedidosVansEntity]:
        return next((l for l in self._logs if l.message_id == message_id), None)

    def create(self, log: LogPrePedidosVansEntity) -> LogPrePedidosVansEntity:
        log = deepcopy(log)
        log.id = self._next_id
        self._next_id += 1
        self._logs.append(log)
        return log

    def update(self, log: LogPrePedidosVansEntity) -> LogPrePedidosVansEntity:
        for i, existing in enumerate(self._logs):
            if existing.id == log.id:
                self._logs[i] = deepcopy(log)
                return self._logs[i]
        raise ValueError(f"Log with id={log.id} not found")

    def delete(self, log_id: int) -> None:
        for log in self._logs:
            if log.id == log_id:
                log.integration_status = "DELETED"
                return


# ═══════════════════════════════════════════════════════════════════════
#  Mock: IntegrationLogRepository (in-memory)
# ═══════════════════════════════════════════════════════════════════════

class MockIntegrationLogRepository:
    """
    Mock in-memory do repositório de IntegrationLog.
    Armazena logs numa lista e auto-incrementa o id.
    """

    def __init__(self) -> None:
        self._logs: list[IntegrationLogEntity] = []
        self._next_id: int = 1

    def get_all(self) -> list[IntegrationLogEntity]:
        return list(self._logs)

    def get_by_id(self, log_id: int) -> Optional[IntegrationLogEntity]:
        return next((l for l in self._logs if l.id == log_id), None)

    def get_by_log_uuid(self, log_uuid: UUID) -> list[IntegrationLogEntity]:
        return [l for l in self._logs if l.log_uuid == log_uuid]

    def get_by_origin_system(self, origin_system: str) -> list[IntegrationLogEntity]:
        return [l for l in self._logs if l.origin_system == origin_system]

    def get_by_status(self, status: str) -> list[IntegrationLogEntity]:
        return [l for l in self._logs if l.status == status]

    def create(self, log: IntegrationLogEntity) -> IntegrationLogEntity:
        log = deepcopy(log)
        log.id = self._next_id
        self._next_id += 1
        self._logs.append(log)
        return log

    def update(self, log: IntegrationLogEntity) -> IntegrationLogEntity:
        for i, existing in enumerate(self._logs):
            if existing.id == log.id:
                self._logs[i] = deepcopy(log)
                return self._logs[i]
        raise ValueError(f"Log with id={log.id} not found")

    def delete(self, log_id: int) -> None:
        for log in self._logs:
            if log.id == log_id:
                log.status = "DELETED"
                return


# ═══════════════════════════════════════════════════════════════════════
#  Mock: GraphQLFetcher (respostas configuráveis)
# ═══════════════════════════════════════════════════════════════════════

class MockGraphQLFetcher:
    """
    Mock do GraphQLFetcher que retorna respostas pré-configuradas.

    Attributes:
        _responses: Fila de respostas a retornar em cada chamada fetch().
        calls: Lista de chamadas recebidas (para assertions).
    """

    def __init__(self, responses: Optional[list[Any]] = None) -> None:
        self._responses: list[Any] = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    async def fetch(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
        extract_path: Optional[list[str]] = None,
    ) -> Any:
        self.calls.append({
            "query": query,
            "variables": variables,
            "operation_name": operation_name,
            "extract_path": extract_path,
        })
        if self._responses:
            resp = self._responses.pop(0)
            if isinstance(resp, BaseException):
                raise resp
            return resp
        return {}


# ═══════════════════════════════════════════════════════════════════════
#  Mock: PubSub (in-memory)
# ═══════════════════════════════════════════════════════════════════════

class MockPubSub:
    """
    Mock do PubSubProtocol que armazena mensagens publicadas em memória.

    Attributes:
        messages: Lista de tuplas (topic, message, attributes) publicadas.
        _next_id: Contador auto-incrementado para message_id.
    """

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self._next_id: int = 1000

    async def publish_message(
        self,
        topic: str,
        message: str,
        attributes: dict,
    ) -> Union[str, int]:
        self.messages.append({
            "topic": topic,
            "message": message,
            "attributes": attributes,
        })
        msg_id = str(self._next_id)
        self._next_id += 1
        return msg_id

    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        return True


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures: Dados de teste (pedidos brutos estilo Fidelize Wholesaler)
# ═══════════════════════════════════════════════════════════════════════

SAMPLE_RAW_ORDERS = [
    {
        "id": "98001",
        "order_code": "5001",
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
        "additional_information": "Pedido urgente",
        "scheduled_delivery_order": False,
        "wholesaler_code": "98765432000199",
        "wholesaler_branch_code": "98765432000100",
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
        "order_code": "5002",
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
        "additional_information": None,
        "scheduled_delivery_order": True,
        "wholesaler_code": "98765432000199",
        "wholesaler_branch_code": None,
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
]

