"""
Exceções de domínio para integrações de VANs.
"""


class EmptyResponse(Exception):
    """Resposta vazia retornada pela VAN."""

    def __init__(self, message: str = "Response is empty"):
        self.message = message
        super().__init__(self.message)


class VanFetchError(Exception):
    """Erro ao buscar dados de uma VAN."""

    def __init__(self, message: str = "Error fetching data from VAN"):
        self.message = message
        super().__init__(self.message)


class VanAuthError(Exception):
    """Erro de autenticação com uma VAN."""

    def __init__(self, message: str = "Authentication error with VAN"):
        self.message = message
        super().__init__(self.message)

