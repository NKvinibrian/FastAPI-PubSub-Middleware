from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    GCP_PROJECT_ID: str
    GCP_CREDENTIALS_PATH: str
    MONGO_URI: str
    MONGO_DB_NAME: str
    BINARY_DECODE: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()