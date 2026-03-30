"""
Protocolo para parsers de Observer.

Define a interface que qualquer Observer parser deve implementar.
Cada método retorna uma lista de ObserverMessageSchema prontos para publicação.
"""

from typing import Protocol

from app.api.v1.schemas.vans.observer_message import ObserverMessageSchema


class ObserverParserProtocol(Protocol):
    """
    Protocolo para parsers do Observer.

    Cada método consulta o estado atual no banco e converte
    em mensagens genéricas para publicação no PubSub.
    """

    def parse_order_returns(self) -> list[ObserverMessageSchema]:
        """Pedidos aceitos/parcialmente aceitos para retorno à VAN."""
        ...

    def parse_order_rejections(self) -> list[ObserverMessageSchema]:
        """Pedidos cancelados/rejeitados para retorno à VAN."""
        ...

    def parse_invoices(self) -> list[ObserverMessageSchema]:
        """Notas fiscais para envio à VAN."""
        ...

    def parse_cancellations(self) -> list[ObserverMessageSchema]:
        """Pedidos cancelados após confirmação para envio à VAN."""
        ...

