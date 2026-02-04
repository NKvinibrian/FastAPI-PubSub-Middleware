"""
Módulo de modelos de dados para logging de requisições.

Este módulo define as estruturas de dados utilizadas para armazenar
informações sobre requisições HTTP e suas respostas.

Classes:
    RequestLog: Dataclass que representa um log de requisição HTTP
"""

from dataclasses import dataclass
from typing import Union


@dataclass
class RequestLog:
    """
    Representa um log completo de uma requisição HTTP.

    Attributes:
        method: Método HTTP da requisição (GET, POST, PUT, etc.)
        path: Caminho da URL requisitada
        status_code: Código de status HTTP da resposta
        success: Indica se a requisição foi bem-sucedida (status < 400)
        duration_ms: Duração da requisição em milissegundos
        headers: Cabeçalhos HTTP da requisição
        sent_body: Corpo da requisição enviada
        response_body: Corpo da resposta retornada
        error_type: Tipo de erro, se houver (validation_error, internal_error, etc.)
        error_message: Mensagem de erro detalhada
        pub_id: ID de publicação para mensagens Pub/Sub
        message_id: ID da mensagem para rastreamento
    """
    method: str
    path: str
    status_code: int
    success: bool
    duration_ms: int
    headers: dict | str | None = None
    sent_body: str | None = None
    response_body: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    pub_id: Union[str, int] | None = None
    message_id: Union[str, int] | None = None
