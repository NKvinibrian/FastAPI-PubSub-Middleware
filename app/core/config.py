"""
Módulo de configuração da aplicação.

Este módulo gerencia todas as configurações da aplicação através de variáveis
de ambiente, utilizando pydantic-settings para validação e carregamento.

Classes:
    Settings: Configurações da aplicação carregadas do arquivo .env

Funções:
    get_settings: Retorna uma instância cacheada das configurações
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas do arquivo .env.

    Attributes:
        GCP_PROJECT_ID: ID do projeto no Google Cloud Platform
        GCP_CREDENTIALS_PATH: Caminho para o arquivo de credenciais GCP
        MONGO_URI: URI de conexão com o MongoDB
        MONGO_DB_NAME: Nome do banco de dados MongoDB
        BINARY_DECODE: Encoding para decodificação de dados binários (ex: 'utf-8')
    """
    GCP_PROJECT_ID: str
    GCP_CREDENTIALS_PATH: str
    MONGO_URI: str
    MONGO_DB_NAME: str
    BINARY_DECODE: str

    class Config:
        """Configuração do Pydantic Settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna uma instância cacheada das configurações.

    Utiliza lru_cache para garantir que as configurações sejam carregadas
    apenas uma vez durante o ciclo de vida da aplicação.

    Returns:
        Settings: Instância das configurações da aplicação
    """
    return Settings()
