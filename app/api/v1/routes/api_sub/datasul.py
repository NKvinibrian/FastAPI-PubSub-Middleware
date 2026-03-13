from fastapi import APIRouter, Depends
from fastapi import status as http_status
from app.api.v1.schemas.api_sub.receiver import PubSub
from app.core.dependencies import get_datasul_service

router = APIRouter(
    prefix='/datasul-subscribe',
    tags=['Datasul subscription']
)

@router.post("/pre-pedido-datasul", status_code=http_status.HTTP_200_OK)
async def pre_pedido_sub(request: PubSub, datasul_service=Depends(get_datasul_service)):
    return {"message": "Pedido recebido com sucesso"}
