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
    def __init__(self, app, logger: MongoLoggingService):
        super().__init__(app)
        self.logger = logger

    @staticmethod
    async def capture_response_body(response: Response) -> bytes:
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        return response_body

    @staticmethod
    async def capture_request_headers(request: Request) -> dict:
        headers = {}
        for header in request.headers.items():
            headers[header[0]] = header[1]
        return headers

    @staticmethod
    async def rebuild_response(response: Response, content: bytes) -> Response:
        return Response(
            content=content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

    async def dispatch(self, request: Request, call_next):
        start = time.time()

        try:
            response = await call_next(request)

            duration = int((time.time() - start) * 1000)

            # Attention: when capturing the response body, we need to rebuild the response (StreamingIO can be read only once)
            captured_response = await self.capture_response_body(response)

            # rebuild the response with the captured body
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
