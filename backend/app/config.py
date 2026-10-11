from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and the backend/.env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise IT Support Agent"
    app_env: str = "local"
    log_level: str = "INFO"

    llm_provider: Literal["gemini"] = "gemini"
    llm_model: str = "gemini-3.1-flash-lite"
    llm_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    llm_timeout_seconds: int = Field(default=30, gt=0)
    gemini_api_key: SecretStr

    database_host: str = "localhost"
    database_port: int = Field(default=5432, gt=0)
    database_name: str
    database_user: str
    database_password: SecretStr
    database_pool_size: int = Field(default=5, gt=0)
    database_statement_timeout_ms: int = Field(default=5000, gt=0)

    classification_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    max_clarification_attempts: int = Field(default=2, ge=0)
    max_tool_iterations: int = Field(default=6, gt=0)


settings = Settings()
