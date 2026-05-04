"""
Fetcher V2 para Fidelize Funcional Wholesaler.

Utiliza o GraphQLFetcher (conector limpo) para buscar pedidos
e confirmar importação. Não conhece banco, logging ou parsing.

Endpoint, método HTTP e headers de cada operação vêm de
hub.request_details (via OperationConfig pré-carregado), mesmo padrão
do Observer subscriber. As queries GraphQL ficam no código.

Implementa VanFetcherProtocol — o parâmetro `context` corresponde
ao `industry_code` desta integração específica.
"""

import asyncio
from typing import Any, Optional

from app.domain.protocol.vans.fetcher import GraphQLFetcherProtocol
from app.infrastructure.vans.operations_loader import OperationConfig


OPERATION_GET_PRE_ORDERS = "get_pre_orders"
OPERATION_SET_ORDERS_AS_IMPORTED = "set_orders_as_imported"


class FidelizeWholesalerFetcher:
    """
    Fetcher específico para a integração Fidelize Funcional Wholesaler.

    Encapsula as queries/mutations GraphQL do manual Wholesaler v2.2.
    Delega o transporte ao GraphQLFetcherProtocol injetado — aceita
    qualquer implementação real ou mock.

    Args:
        fetcher: Implementação de GraphQLFetcherProtocol.
        operations: Mapa nome → OperationConfig carregado de
            hub.request_details. Quando informado, sobrescreve URL,
            método e headers em cada chamada. Quando None, o fetcher
            cai no comportamento legado (usa base_url do conector).
    """

    def __init__(
        self,
        fetcher: GraphQLFetcherProtocol,
        operations: Optional[dict[str, OperationConfig]] = None,
    ) -> None:
        self._fetcher = fetcher
        self._operations = operations or {}

    def _op(self, name: str) -> Optional[OperationConfig]:
        return self._operations.get(name)

    async def get_pre_orders(
        self,
        context: Optional[Any] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Consulta pedidos disponíveis (não importados) na Fidelize.

        Args:
            context: Código da indústria (ex: SAN, RCH).
            page: Página atual para paginação.
            per_page: Quantidade de pedidos por página.

        Returns:
            Lista de dicts com os pedidos (campo data da query orders).

        Raises:
            RuntimeError: Se a resposta GraphQL contiver erros.
        """
        industry_code: str = context or ""

        query = f"""
        query {{
          orders(
            current_page: {page}
            per_page: {per_page}
            imported: false
            status: ORDER_NOT_IMPORTED
            industry_code: \"{industry_code}\"
            filter: {{}}
          ) {{
            total
            from
            to
            data {{
              id
              order_code
              status
              tradetools_created_at
              notification_obs
              notification_status
              industry_code
              customer_code
              customer_alternative_code
              customer_email
              distribution_center_code
              order_payment_term
              commercial_condition_code
              customer_order_code
              destination_customer
              profit_share_margin
              is_free_good_discount
              recalculates_discount
              customer_code_type
              indicator
              salesman_code
              scheduled_delivery_order
              sends_either_value_or_discount
              sends_only_discount
              additional_information
              wholesaler_branch_code
              wholesaler_code
              products {{
                ean
                gross_value
                amount
                discount_percentage
                net_value
                monitored
                payment_term
              }}
            }}
          }}
        }}
        """

        op = self._op(OPERATION_GET_PRE_ORDERS)
        data = await self._fetcher.fetch(
            query=query,
            extract_path=["orders", "data"],
            url=op.url if op else None,
            extra_headers=op.headers if op else None,
        )

        if not data:
            return []

        return data if isinstance(data, list) else []

    async def set_orders_as_imported(
        self,
        order_codes: list[int | str],
        context: Optional[Any] = None,
    ) -> None:
        """
        Marca pedidos como importados na Fidelize (setOrderAsImported).

        Args:
            order_codes: Lista de order_codes a confirmar.
            context: Código da indústria.

        Raises:
            RuntimeError: Se alguma mutation falhar.
        """
        industry_code: str = context or ""
        op = self._op(OPERATION_SET_ORDERS_AS_IMPORTED)
        op_url = op.url if op else None
        op_headers = op.headers if op else None

        async def _confirm(order_code: int | str) -> dict[str, Any]:
            mutation = f"""
            mutation {{
              setOrderAsImported(
                order_code: {int(order_code)}
                industry_code: \"{industry_code}\"
              ) {{
                id
                order_code
                customer_code
                customer_alternative_code
              }}
            }}
            """
            return await self._fetcher.fetch(
                query=mutation,
                extract_path=["setOrderAsImported"],
                url=op_url,
                extra_headers=op_headers,
            )

        if not order_codes:
            return

        tasks = [_confirm(code) for code in order_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                raise result
