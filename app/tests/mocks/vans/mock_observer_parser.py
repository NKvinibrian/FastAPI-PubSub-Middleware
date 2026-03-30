"""
Mock do ObserverParser para testes.

Simula o comportamento do FidelizeObserverParser:
    - Recebe "registros do banco" (listas de dicts in-memory)
    - Monta ObserverMessageSchema usando a mesma lógica de _make_message

Os dados de entrada simulam o que viria de queries no banco
(pre_pedidos, pedidos_datasul, NFs, cancelamentos).
"""

from typing import Any

from app.api.v1.schemas.vans.observer_message import (
    ObserverAction,
    ObserverMessageSchema,
    ObserverSetupSchema,
)


class MockObserverParser:
    """
    Mock do ObserverParserProtocol.

    Recebe registros brutos (simulando rows do banco) e converte
    em ObserverMessageSchema, igual ao parser real faria.

    Args:
        origin_system: Nome da integração.
        integration_id: ID da integração no banco.
        order_returns_rows: Registros de pedidos aceitos (do banco).
        order_rejections_rows: Registros de pedidos rejeitados (do banco).
        invoices_rows: Registros de notas fiscais (do banco).
        cancellations_rows: Registros de cancelamentos (do banco).
    """

    def __init__(
        self,
        origin_system: str,
        integration_id: int,
        order_returns_rows: list[dict[str, Any]] | None = None,
        order_rejections_rows: list[dict[str, Any]] | None = None,
        invoices_rows: list[dict[str, Any]] | None = None,
        cancellations_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self._origin_system = origin_system
        self._integration_id = integration_id
        self._order_returns_rows = order_returns_rows or []
        self._order_rejections_rows = order_rejections_rows or []
        self._invoices_rows = invoices_rows or []
        self._cancellations_rows = cancellations_rows or []

    def _make_message(
        self,
        action: ObserverAction,
        order_code: int | str,
        industry_code: str,
        payload: dict[str, Any],
    ) -> ObserverMessageSchema:
        """Mesma lógica do parser real: envolve payload num ObserverMessageSchema."""
        return ObserverMessageSchema(
            integration=self._origin_system,
            integration_id=self._integration_id,
            action=action,
            setup=ObserverSetupSchema(
                check_id="order_code",
                query_parameters={
                    "order_code": str(order_code),
                    "industry_code": industry_code,
                },
            ),
            payload=payload,
        )

    def _parse_rows(
        self,
        rows: list[dict[str, Any]],
        action: ObserverAction,
    ) -> list[ObserverMessageSchema]:
        """Converte registros brutos em mensagens, simulando a query do banco."""
        messages = []
        for row in rows:
            msg = self._make_message(
                action=action,
                order_code=row["order_code"],
                industry_code=row["industry_code"],
                payload=row,
            )
            messages.append(msg)
        return messages

    def parse_order_returns(self) -> list[ObserverMessageSchema]:
        return self._parse_rows(self._order_returns_rows, ObserverAction.ORDER_RETURN)

    def parse_order_rejections(self) -> list[ObserverMessageSchema]:
        return self._parse_rows(self._order_rejections_rows, ObserverAction.ORDER_RETURN_REJECTION)

    def parse_invoices(self) -> list[ObserverMessageSchema]:
        return self._parse_rows(self._invoices_rows, ObserverAction.RETURN_INVOICES)

    def parse_cancellations(self) -> list[ObserverMessageSchema]:
        return self._parse_rows(self._cancellations_rows, ObserverAction.RETURN_CANCELLATION)