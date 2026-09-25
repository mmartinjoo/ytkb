from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    environment: str = "local"
    log_level: str = "INFO"

    database_url: str = "postgresql://user:pass@127.0.0.1:5432/ytkb"
    database_host: str = "127.0.0.1"
    database_port: int = "5432"
    database_user: str = "user"
    database_password: str = "pass"
    database_db: str = "ytkb"

    s3_endpoint_url: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    
    qdrant_host: str
    qdrant_port: int
    qdrant_vector_dims: int
    
    redis_url: str
    
    openai_api_key: str
    mistral_api_key: str
    
settings = Settings()