from fastapi import APIRouter
from fastapi import status as http_status
from app.api.v1.schemas.api_sub.receiver import PubSub

router = APIRouter(
    prefix='/sub',
    tags=['sub', 'receiver', 'subscription']
)

@router.post("/example-subscribe-message", status_code=http_status.HTTP_200_OK)
async def example_publish_message(request: PubSub):
    return {"message": "Hello World"}
