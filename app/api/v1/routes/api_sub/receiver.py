"""
Módulo de rotas para subscrição de mensagens.

Este módulo define os endpoints da API para recebimento de mensagens
do sistema Pub/Sub (push subscriptions).

Attributes:
    router: Router do FastAPI configurado para endpoints de subscrição
"""

from fastapi import APIRouter
from fastapi import status as http_status
from app.api.v1.schemas.api_sub.receiver import PubSub

router = APIRouter(
    prefix='/sub',
    tags=['subscription']
)


@router.post("/example-subscribe-message", status_code=http_status.HTTP_200_OK)
async def example_publish_message(request: PubSub):
    """
    Endpoint de exemplo para recebimento de mensagens Pub/Sub.

    Este endpoint é chamado automaticamente pelo Google Cloud Pub/Sub
    quando há uma nova mensagem na subscrição configurada.

    Args:
        request: Payload do Pub/Sub contendo a mensagem e metadados

    Returns:
        dict: Resposta de confirmação de recebimento

    Note:
        O Google Cloud Pub/Sub espera uma resposta HTTP 200 para confirmar
        o processamento da mensagem. Caso contrário, a mensagem será reenviada.

    Example request:
        ```json
        {
            "subscription": "projects/myproject/subscriptions/mysub",
            "message": {
                "data": "SGVsbG8gV29ybGQ=",
                "messageId": "136969346945",
                "attributes": {
                    "pub_id": "123e4567-e89b-12d3-a456-426614174000",
                    "topic_id": "topic_1",
                    "industrial_code": "12345"
                }
            }
        }
        ```
    """
    return {"message": "Hello World"}
