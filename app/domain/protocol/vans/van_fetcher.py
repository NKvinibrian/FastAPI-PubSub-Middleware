"""
Protocolo genérico para Fetchers de VAN.

Define o contrato que todo fetcher de VAN deve implementar,
independente do transporte (REST, GraphQL, FTP, etc.) ou
da integração específica.

O fetcher só sabe buscar dados brutos e confirmar importação.
Não conhece banco, logging ou regras de negócio.
"""

from typing import Protocol, Any, Optional


class VanFetcherProtocol(Protocol):
    """
    Contrato genérico para fetchers de VAN.

    Qualquer fetcher de integração (Fidelize, Interplayers, IQVIA, etc.)
    deve implementar estes dois métodos.

    O parâmetro `context` é proposital e genérico — algumas VANs
    iteram por `industry_code`, outras por `distributor_code`,
    outras não têm loop algum. O chamador decide o que passa.
    """

    async def get_pre_orders(
        self,
        context: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """
        Busca pedidos disponíveis (não importados) na VAN.

        Args:
            context: Parâmetro de iteração da VAN (ex: industry_code,
                     distributor_code, None para VANs sem loop).

        Returns:
            Lista de dicts brutos com os pedidos.
        """
        ...

    async def set_orders_as_imported(
        self,
        order_codes: list[Any],
        context: Optional[Any] = None,
    ) -> None:
        """
        Confirma pedidos como importados na VAN.

        Args:
            order_codes: Lista de códigos de pedido a confirmar.
            context: Mesmo parâmetro de iteração usado em get_pre_orders.
        """
        ...

