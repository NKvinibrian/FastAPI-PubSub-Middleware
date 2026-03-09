from typing import Protocol


class AuthProviderProtocol(Protocol):

    async def build_auth(self) -> dict:
        ...
