from fastapi import APIRouter, Depends
from fastapi import status as http_status
from app.api.v1.schemas.api_pub.sender import SenderSchema
from app.core.depedencies import get_pubsub
from app.domain.protocol.pubsub.pubsub import PubSubProtocol

router = APIRouter(
    prefix='/pub',
    tags=['pub', 'sender', 'publish']
)

@router.post("/example-publish-message", status_code=http_status.HTTP_201_CREATED)
async def example_publish_message(request: SenderSchema, pubsub: PubSubProtocol = Depends(get_pubsub)):
    message_id = await pubsub.publish_message(topic="topic_1", message=request.model_dump_json(), attributes={"industrial_code": "12345"})
    return {"message_id": f"{message_id}"}

