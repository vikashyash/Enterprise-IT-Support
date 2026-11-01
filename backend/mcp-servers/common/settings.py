from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings shared by every MCP server. Values come from environment variables, then mcp-servers/.env, then backend/.env."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")
    

    log_level: str = "INFO"

    database_host: str = "localhost"
    database_port: int = Field(default=5432, gt=0)
    database_name: str
    database_user: str
    database_password: SecretStr
    database_pool_size: int = Field(default=5, gt=0)
    database_statement_timeout_ms: int = Field(default=5000, gt=0)

    mcp_host: str = "127.0.0.1"
    itsm_port: int = Field(default=8101, gt=0)
    device_port: int = Field(default=8102, gt=0)
    infrastructure_port: int = Field(default=8103, gt=0)
    iam_port: int = Field(default=8104, gt=0)


settings = Settings()
