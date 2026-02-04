"""
Módulo de rotas para publicação de mensagens.

Este módulo define os endpoints da API para publicação de mensagens
no sistema Pub/Sub.

Attributes:
    router: Router do FastAPI configurado para endpoints de publicação
"""

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from app.api.v1.schemas.api_pub.sender import SenderSchema
from app.core.dependencies import get_pubsub
from app.domain.protocol.pubsub.pubsub import PubSubProtocol

router = APIRouter(
    prefix='/pub',
    tags=['pub', 'sender', 'publish']
)


@router.post("/example-publish-message", status_code=http_status.HTTP_201_CREATED)
async def example_publish_message(request: SenderSchema, pubsub: PubSubProtocol = Depends(get_pubsub)):
    """
    Endpoint de exemplo para publicação de mensagens.

    Publica uma mensagem no tópico 'topic_1' com os dados fornecidos.

    Args:
        request: Dados do remetente e mensagem
        pubsub: Serviço de Pub/Sub injetado por dependência

    Returns:
        dict: Dicionário contendo o message_id da mensagem publicada

    Example:
        ```json
        {
            "name": "João Silva",
            "email": "joao@example.com",
            "message": "Mensagem de teste"
        }
        ```

    Response:
        ```json
        {
            "message_id": "123456789"
        }
        ```
    """
    message_id = await pubsub.publish_message(
        topic="topic_1",
        message=request.model_dump_json(),
        attributes={"industrial_code": "12345"}
    )
    return {"message_id": f"{message_id}"}

