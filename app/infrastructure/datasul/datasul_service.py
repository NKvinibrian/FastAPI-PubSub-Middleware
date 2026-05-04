"""
Serviço real de integração com o Datasul.

TODO: Implementar login e envio de pré-pedidos via API Datasul.
"""

from app.domain.protocol.datasul.datasul import DatasulProtocol


class DatasulService(DatasulProtocol):

    def login(self, username: str, password: str) -> str:
        raise NotImplementedError("DatasulService.login ainda não implementado")

    def send_pre_pedido(self, token: str, data: dict) -> bool:
        raise NotImplementedError("DatasulService.send_pre_pedido ainda não implementado")
