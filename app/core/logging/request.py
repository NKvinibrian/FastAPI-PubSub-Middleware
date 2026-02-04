from dataclasses import dataclass
from typing import Union


@dataclass
class RequestLog:
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
