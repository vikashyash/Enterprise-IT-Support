import json
import logging

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine

from common.settings import settings

logger = logging.getLogger(__name__)

database_url = URL.create("postgresql+asyncpg", username=settings.database_user, password=settings.database_password.get_secret_value(), host=settings.database_host, port=settings.database_port, database=settings.database_name)

engine = create_async_engine(database_url, pool_size=settings.database_pool_size, max_overflow=settings.database_pool_size, pool_pre_ping=True, pool_recycle=1800, connect_args={"timeout": 10, "server_settings": {"application_name": "it-support-mcp", "statement_timeout": str(settings.database_statement_timeout_ms)}})

EMPLOYEE_QUERY = """
SELECT e.id AS employee_id, e.company_id, e.employee_code, e.name, e.email, e.job_title, e.role, e.status, d.name AS department
FROM itsupport.employees e
JOIN itsupport.departments d ON d.id = e.department_id
WHERE e.employee_code = :employee_code AND e.status = 'ACTIVE'
LIMIT 1
"""


async def fetch_rows(query: str, parameters: dict | None = None) -> list[dict]:
    """Run a read query and return the rows as JSON-safe dictionaries (dates and IPs become strings)."""
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(query), parameters or {})
            return json.loads(json.dumps([dict(row) for row in result.mappings()], default=str))
    except Exception:
        logger.exception("Read query failed")
        raise


async def execute_write(query: str, parameters: dict) -> dict | None:
    """Run an INSERT/UPDATE/DELETE in its own transaction and return the first RETURNING row, or None if no row came back."""
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(query), parameters)
            returned_row = result.mappings().first()
            return json.loads(json.dumps(dict(returned_row), default=str)) if returned_row else None
    except Exception:
        logger.exception("Write query failed")
        raise


async def find_active_employee(employee_code: str) -> dict | None:
    """Return the active employee row for an employee code, or None if the employee is unknown or inactive."""
    employees = await fetch_rows(EMPLOYEE_QUERY, {"employee_code": employee_code})
    return employees[0] if employees else None