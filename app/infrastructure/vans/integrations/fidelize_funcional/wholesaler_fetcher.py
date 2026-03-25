"""
Fetcher V2 para Fidelize Funcional Wholesaler.

Utiliza o GraphQLFetcher (conector limpo) para buscar pedidos
e confirmar importação. Não conhece banco, logging ou parsing.

Implementa VanFetcherProtocol — o parâmetro `context` corresponde
ao `industry_code` desta integração específica.
"""

import asyncio
from typing import Any, Optional

from app.domain.protocol.vans.fetcher import GraphQLFetcherProtocol


class FidelizeWholesalerFetcher:
    """
    Fetcher específico para a integração Fidelize Funcional Wholesaler.

    Encapsula as queries/mutations GraphQL do manual Wholesaler v2.2.
    Delega o transporte ao GraphQLFetcherProtocol injetado — aceita
    qualquer implementação real ou mock.

    Attributes:
        _fetcher: Implementação de GraphQLFetcherProtocol.
    """

    def __init__(self, fetcher: GraphQLFetcherProtocol) -> None:
        self._fetcher = fetcher

    async def get_pre_orders(
        self,
        context: Optional[Any] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Consulta pedidos disponíveis (não importados) na Fidelize.

        Implementa VanFetcherProtocol — `context` é o industry_code.

        Args:
            context: Código da indústria (ex: SAN, RCH). Mapeado de VanFetcherProtocol.
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

        data = await self._fetcher.fetch(
            query=query,
            extract_path=["orders", "data"],
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

        Implementa VanFetcherProtocol — `context` é o industry_code.

        Args:
            order_codes: Lista de order_codes a confirmar.
            context: Código da indústria. Mapeado de VanFetcherProtocol.

        Raises:
            RuntimeError: Se alguma mutation falhar.
        """
        industry_code: str = context or ""

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
            )

        if not order_codes:
            return

        tasks = [_confirm(code) for code in order_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                raise result

