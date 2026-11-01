import json
import logging

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

database_url = URL.create("postgresql+asyncpg", username=settings.database_user, password=settings.database_password.get_secret_value(), host=settings.database_host, port=settings.database_port, database=settings.database_name)

engine = create_async_engine(database_url, pool_size=settings.database_pool_size, max_overflow=settings.database_pool_size, pool_pre_ping=True, pool_recycle=1800, connect_args={"timeout": 10, "server_settings": {"application_name": "it-support-backend", "statement_timeout": str(settings.database_statement_timeout_ms)}})


async def fetch_rows(query: str, parameters: dict | None = None) -> list[dict]:
    """Run a read query and return the rows as JSON-safe dictionaries."""
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(query), parameters or {})
            return json.loads(json.dumps([dict(row) for row in result.mappings()], default=str))
    except Exception:
        logger.exception("Read query failed")
        raise


async def execute_write(query: str, parameters: dict | None = None) -> dict | None:
    """Run a write in its own transaction and return the first RETURNING row, or None."""
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(query), parameters or {})
            if not result.returns_rows:
                return None
            returned_row = result.mappings().first()
            return json.loads(json.dumps(dict(returned_row), default=str)) if returned_row else None
    except Exception:
        logger.exception("Write query failed")
        raise
