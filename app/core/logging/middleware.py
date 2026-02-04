"""
Módulo de middleware para logging de requisições HTTP.

Este módulo implementa um middleware do FastAPI que captura e registra
informações sobre todas as requisições HTTP processadas pela aplicação,
incluindo dados de request, response, timing e erros.

Classes:
    RequestLoggingMiddleware: Middleware para logging automático de requisições
"""

import time
from fastapi import Request
from fastapi.responses import Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging.logger import MongoLoggingService
from app.core.logging.request import RequestLog
from app.core.config import get_settings

Settings = get_settings()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging automático de requisições HTTP.

    Este middleware captura informações detalhadas sobre cada requisição,
    incluindo método, path, headers, corpo da resposta, tempo de execução
    e eventuais erros.

    Attributes:
        logger: Serviço de logging para persistir os dados
    """

    def __init__(self, app, logger: MongoLoggingService):
        """
        Inicializa o middleware de logging.

        Args:
            app: Aplicação FastAPI
            logger: Serviço de logging para persistência dos dados
        """
        super().__init__(app)
        self.logger = logger

    @staticmethod
    async def capture_response_body(response: Response) -> bytes:
        """
        Captura o corpo da resposta HTTP.

        Como a resposta usa StreamingIO que pode ser lido apenas uma vez,
        é necessário capturar o conteúdo para logging antes de retorná-lo.

        Args:
            response: Objeto Response do FastAPI

        Returns:
            bytes: Conteúdo completo do corpo da resposta
        """
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        return response_body

    @staticmethod
    async def capture_request_headers(request: Request) -> dict:
        """
        Captura os cabeçalhos da requisição HTTP.

        Args:
            request: Objeto Request do FastAPI

        Returns:
            dict: Dicionário com todos os cabeçalhos da requisição
        """
        headers = {}
        for header in request.headers.items():
            headers[header[0]] = header[1]
        return headers

    @staticmethod
    async def rebuild_response(response: Response, content: bytes) -> Response:
        """
        Reconstrói o objeto Response após capturar seu conteúdo.

        Necessário porque o StreamingIO não pode ser reutilizado após a leitura.

        Args:
            response: Response original
            content: Conteúdo capturado do corpo da resposta

        Returns:
            Response: Nova instância de Response com o mesmo conteúdo
        """
        return Response(
            content=content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

    async def dispatch(self, request: Request, call_next):
        """
        Processa a requisição, captura informações e registra o log.

        Este método é chamado para cada requisição HTTP. Ele:
        1. Captura o timestamp inicial
        2. Processa a requisição
        3. Captura a resposta e headers
        4. Calcula o tempo de execução
        5. Salva o log no banco de dados
        6. Trata erros de validação e internos

        Args:
            request: Requisição HTTP recebida
            call_next: Função para chamar o próximo handler

        Returns:
            Response: Resposta HTTP a ser retornada ao cliente

        Raises:
            RequestValidationError: Repassado após logging quando há erro de validação
            Exception: Repassado após logging para erros gerais
        """
        start = time.time()

        try:
            response = await call_next(request)

            duration = int((time.time() - start) * 1000)

            # Atenção: ao capturar o corpo da resposta, precisamos reconstruir a resposta
            # (StreamingIO pode ser lido apenas uma vez)
            captured_response = await self.capture_response_body(response)

            # Reconstrói a resposta com o corpo capturado
            response = await self.rebuild_response(response, captured_response)

            headers = await self.capture_request_headers(request)

            await self.logger.save(
                RequestLog(
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    success=response.status_code < 400,
                    duration_ms=duration,
                    response_body=captured_response.decode(Settings.BINARY_DECODE),
                    headers=headers,
                )
            )

            return response

        except RequestValidationError as exc:
            duration = int((time.time() - start) * 1000)

            await self.logger.save(
                RequestLog(
                    method=request.method,
                    path=request.url.path,
                    status_code=422,
                    success=False,
                    error_type="validation_error",
                    error_message=str(exc),
                    duration_ms=duration,
                )
            )

            raise

        except Exception as exc:
            duration = int((time.time() - start) * 1000)

            await self.logger.save(
                RequestLog(
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    success=False,
                    error_type="internal_error",
                    error_message=str(exc),
                    duration_ms=duration,
                )
            )

            raise


            raise

