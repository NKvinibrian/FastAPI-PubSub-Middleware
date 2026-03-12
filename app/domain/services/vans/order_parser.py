"""
Parser genérico de pedidos de VANs.

Converte pedidos brutos (list[dict]) vindos de qualquer VAN para
o formato padronizado PrePedidoSchema. Salva cada pedido individual
na tabela LogPrePedidosVans.

Cada VAN deve fornecer um `field_map` que diz como mapear os campos
do dict bruto para o PrePedidoSchema. Para VANs com lógica mais
específica, basta sobrescrever `_map_order()`.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.api.v1.schemas.vans.pre_pedido import PrePedidoItemSchema, PrePedidoSchema
from app.domain.entities.logs.vans import LogPrePedidosVansEntity
from app.domain.protocol.logs.repository import LogPrePedidosVansRepositoryProtocol


class OrderParser:
    """
    Parser genérico que converte pedidos brutos em PrePedidoSchema.

    Salva um LogPrePedidosVansEntity para cada pedido parseado.

    Attributes:
        _log_repository: Repositório de LogPrePedidosVans.
        _origin_system: Nome do sistema de origem.
        _log_uuid: UUID do grupo de processamento.
        _integration_id: ID da integração no banco.
    """

    def __init__(
        self,
        log_repository: LogPrePedidosVansRepositoryProtocol,
        origin_system: str,
        log_uuid: UUID,
        integration_id: int,
    ) -> None:
        self._log_repository = log_repository
        self._origin_system = origin_system
        self._log_uuid = log_uuid
        self._integration_id = integration_id

    def parse(self, raw_orders: list[dict[str, Any]]) -> list[PrePedidoSchema]:
        """
        Converte lista de pedidos brutos em lista de PrePedidoSchema.

        Para cada pedido:
        1. Mapeia campos via _map_order()
        2. Salva LogPrePedidosVansEntity no repositório

        Args:
            raw_orders: Lista de dicts vindos do fetcher.

        Returns:
            Lista de PrePedidoSchema (um por pedido).
        """
        parsed: list[PrePedidoSchema] = []

        for raw in raw_orders:
            schema = self._map_order(raw)
            if schema is None:
                continue

            # Salva log individual do pedido
            log_entity = LogPrePedidosVansEntity(
                id=0,
                pedido_van_id=schema.order_code,
                message_id=None,
                log_uuid=self._log_uuid,
                integration_id=self._integration_id,
                integration_status="PARSED",
            )
            self._log_repository.create(log_entity)

            parsed.append(schema)

        return parsed

    def _map_order(self, raw: dict[str, Any]) -> Optional[PrePedidoSchema]:
        """
        Mapeia um dict bruto para PrePedidoSchema.

        Implementação base — pode ser sobrescrita por parsers
        específicos de cada VAN.

        Args:
            raw: Dict com dados brutos de um pedido.

        Returns:
            PrePedidoSchema ou None se o pedido for inválido.
        """
        products = []
        for p in raw.get("products", []):
            products.append(
                PrePedidoItemSchema(
                    ean=str(p.get("ean", "")),
                    amount=int(p.get("amount", 0)),
                    gross_value=p.get("gross_value"),
                    discount_percentage=p.get("discount_percentage"),
                    net_value=p.get("net_value"),
                    monitored=bool(p.get("monitored", False)),
                    payment_term=p.get("payment_term"),
                )
            )

        created_at = self._parse_datetime(raw.get("tradetools_created_at"))

        return PrePedidoSchema(
            order_code=str(raw.get("order_code", "")),
            origin_system_id=str(raw.get("id", "")),
            origin_system=self._origin_system,
            industry_code=raw.get("industry_code", ""),
            customer_code=raw.get("customer_code"),
            customer_alternative_code=raw.get("customer_alternative_code"),
            customer_email=raw.get("customer_email"),
            customer_code_type=raw.get("customer_code_type"),
            wholesaler_code=raw.get("wholesaler_code"),
            wholesaler_branch_code=raw.get("wholesaler_branch_code"),
            status=raw.get("status"),
            notification_obs=raw.get("notification_obs"),
            notification_status=raw.get("notification_status"),
            order_payment_term=raw.get("order_payment_term"),
            commercial_condition_code=raw.get("commercial_condition_code"),
            additional_information=raw.get("additional_information"),
            scheduled_delivery_order=raw.get("scheduled_delivery_order"),
            tradetools_created_at=created_at,
            products=products,
        )

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string, handling trailing Z."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

