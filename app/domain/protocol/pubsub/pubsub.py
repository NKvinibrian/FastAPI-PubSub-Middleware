"""
Módulo de protocolo para Pub/Sub.

Este módulo define o protocolo (interface) para operações de publicação
e subscrição de mensagens no padrão Pub/Sub.

Classes:
    PubSubProtocol: Protocolo para operações de Pub/Sub
"""

from typing import Protocol, Union


class PubSubProtocol(Protocol):
    """
    Protocolo para operações de Pub/Sub.

    Define a interface para publicação de mensagens e validação
    de tokens de autenticação do serviço Pub/Sub.
    """

    async def publish_message(self, topic: str, message: str, attributes: dict) -> Union[str, int]:
        """
        Publica uma mensagem em um tópico.

        Args:
            topic: Nome do tópico onde a mensagem será publicada
            message: Conteúdo da mensagem a ser publicada
            attributes: Atributos adicionais da mensagem (metadados)

        Returns:
            Union[str, int]: ID da mensagem publicada
        """
        ...

    def validate_pubsub_token(self, token: str, email: str, aud: str) -> bool:
        """
        Valida o token de autenticação do Pub/Sub.

        Args:
            token: Token JWT a ser validado
            email: Email esperado no token
            aud: Audience esperada no token

        Returns:
            bool: True se o token for válido, False caso contrário
        """
        ...
