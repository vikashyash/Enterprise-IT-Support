import hashlib
import logging
from typing import Annotated, Literal

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from pydantic import BaseModel, Field

from app.database import execute_write, fetch_rows

logger = logging.getLogger(__name__)

TicketCategory = Literal["network", "email", "hardware", "software", "access", "security", "general"]
TicketPriority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

CATEGORY_TEAMS = {"network": "Network", "email": "Collaboration", "hardware": "EndUserSupport", "software": "EndUserSupport", "access": "IdentityAccess", "security": "Security", "general": "ServiceDesk"}
UNKNOWN_EMPLOYEE_MESSAGE = "No active employee record matches the signed-in user."

EMPLOYEE_QUERY = """
SELECT e.id AS employee_id, e.company_id, e.employee_code, e.name, e.email, e.job_title, e.role, e.status, d.name AS department
FROM itsupport.employees e
JOIN itsupport.departments d ON d.id = e.department_id
WHERE e.employee_code = :employee_code AND e.status = 'ACTIVE'
LIMIT 1
"""

DEVICES_QUERY = """
SELECT d.asset_tag, d.hostname, d.device_type, d.manufacturer, d.model, d.operating_system, d.os_version, d.cpu, d.ram_gb,
       d.storage_total_gb, d.storage_free_gb,
       ROUND(100.0 * (d.storage_total_gb - d.storage_free_gb) / NULLIF(d.storage_total_gb, 0), 1)::float AS storage_used_percent,
       host(d.ip_address) AS ip_address, d.last_seen_at, d.status
FROM itsupport.devices d
WHERE d.employee_id = :employee_id
  AND (CAST(:hostname AS VARCHAR) IS NULL OR UPPER(d.hostname) = UPPER(CAST(:hostname AS VARCHAR)))
ORDER BY (d.status = 'ACTIVE') DESC, d.last_seen_at DESC NULLS LAST
"""

VPN_SERVICE_QUERY = """
SELECT s.id AS service_id, s.name, s.status, s.health, s.description, s.last_checked_at
FROM itsupport.services s
WHERE s.company_id = :company_id AND s.name = 'VPN'
"""

VPN_INCIDENTS_QUERY = """
SELECT i.incident_number, i.title, i.severity, i.status, i.started_at
FROM itsupport.incidents i
WHERE i.affected_service_id = :service_id AND i.status <> 'RESOLVED'
ORDER BY i.started_at DESC
"""

INSERT_TICKET_QUERY = """
WITH new_ticket AS (SELECT nextval(pg_get_serial_sequence('itsupport.tickets', 'id')) AS id)
INSERT INTO itsupport.tickets (id, ticket_number, company_id, employee_id, title, description, category, priority, status, assigned_team, idempotency_key)
VALUES ((SELECT id FROM new_ticket), (SELECT 'INC-' || (100000 + id) FROM new_ticket), :company_id, :employee_id, :title, :description, :category, :priority, 'OPEN', :assigned_team, :idempotency_key)
ON CONFLICT (company_id, idempotency_key) DO NOTHING
RETURNING id AS ticket_id, ticket_number, title, category, priority, status, assigned_team, created_at
"""

EXISTING_TICKET_QUERY = """
SELECT t.id AS ticket_id, t.ticket_number, t.title, t.category, t.priority, t.status, t.assigned_team, t.created_at
FROM itsupport.tickets t
WHERE t.company_id = :company_id AND t.idempotency_key = :idempotency_key
"""


def tool_error(error_type: str, message: str) -> dict:
    """Build the standard failure payload every tool returns, so the agent can tell a failure apart from real data."""
    return {"ok": False, "error": {"type": error_type, "message": message}}


async def find_active_employee(employee_code: str) -> dict | None:
    """Return the active employee row for the chatting user, or None if the user is unknown or inactive."""
    employees = await fetch_rows(EMPLOYEE_QUERY, {"employee_code": employee_code})
    return employees[0] if employees else None


class CreateTicketInput(BaseModel):
    """Arguments the agent must supply to open an IT ticket. user_id and conversation_id come from graph state, not the LLM."""

    title: str = Field(min_length=5, max_length=200, description="Short summary of the issue, e.g. 'VPN disconnects every few minutes'")
    description: str = Field(min_length=10, max_length=4000, description="What the user reported and what has already been checked")
    category: TicketCategory = Field(description="IT area the issue belongs to")
    priority: TicketPriority = Field(default="MEDIUM", description="Business impact of the issue")
    user_id: Annotated[str, InjectedState("user_id")]
    conversation_id: Annotated[str, InjectedState("conversation_id")]


@tool
async def get_employee(user_id: Annotated[str, InjectedState("user_id")]) -> dict:
    """Look up the employee who is chatting: name, email, job title, department, role and status."""
    try:
        employee = await find_active_employee(user_id)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        return {"ok": True, "employee": {key: value for key, value in employee.items() if key not in ("employee_id", "company_id")}}
    except Exception:
        logger.exception("get_employee failed for %s", user_id)
        return tool_error("internal_error", "Employee directory is unavailable right now.")


@tool
async def get_device(user_id: Annotated[str, InjectedState("user_id")], hostname: str | None = None) -> dict:
    """List the devices registered to the employee with OS, storage usage, IP address, status and last check-in time. Pass hostname to inspect one specific device."""
    try:
        employee = await find_active_employee(user_id)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        devices = await fetch_rows(DEVICES_QUERY, {"employee_id": employee["employee_id"], "hostname": hostname})
        if not devices:
            return tool_error("not_found", f"No device named {hostname} is registered to this employee." if hostname else "No devices are registered to this employee.")
        return {"ok": True, "devices": devices}
    except Exception:
        logger.exception("get_device failed for %s", user_id)
        return tool_error("internal_error", "Device inventory is unavailable right now.")


@tool
async def check_vpn_status(user_id: Annotated[str, InjectedState("user_id")]) -> dict:
    """Check the health of the corporate VPN service and list any active VPN incidents. Call this before troubleshooting the user's device for VPN problems."""
    try:
        employee = await find_active_employee(user_id)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        vpn_services = await fetch_rows(VPN_SERVICE_QUERY, {"company_id": employee["company_id"]})
        if not vpn_services:
            return tool_error("not_found", "The VPN service is not registered in the service catalog.")
        vpn_service = vpn_services[0]
        active_incidents = await fetch_rows(VPN_INCIDENTS_QUERY, {"service_id": vpn_service.pop("service_id")})
        is_operational = vpn_service["status"] == "OPERATIONAL" and not active_incidents
        return {"ok": True, "service": vpn_service, "is_operational": is_operational, "active_incidents": active_incidents}
    except Exception:
        logger.exception("check_vpn_status failed for %s", user_id)
        return tool_error("service_unavailable", "VPN status could not be checked right now.")


@tool(args_schema=CreateTicketInput)
async def create_ticket(title: str, description: str, category: str, priority: str, user_id: str, conversation_id: str) -> dict:
    """Open an IT support ticket for the employee. Use it when the user asks for a ticket or the issue cannot be resolved. Calling it again for the same category in the same conversation returns the existing ticket instead of a duplicate."""
    try:
        employee = await find_active_employee(user_id)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)

        idempotency_key = hashlib.sha256(f"{conversation_id}|{category}".encode("utf-8")).hexdigest()
        ticket_parameters = {
            "company_id": employee["company_id"],
            "employee_id": employee["employee_id"],
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "assigned_team": CATEGORY_TEAMS[category],
            "idempotency_key": idempotency_key,
        }
        created_ticket = await execute_write(INSERT_TICKET_QUERY, ticket_parameters)
        if created_ticket is not None:
            logger.info("Created ticket %s for %s", created_ticket["ticket_number"], user_id)
            return {"ok": True, "created": True, "ticket": created_ticket}

        existing_tickets = await fetch_rows(EXISTING_TICKET_QUERY, {"company_id": employee["company_id"], "idempotency_key": idempotency_key})
        return {"ok": True, "created": False, "ticket": existing_tickets[0]}
    except Exception:
        logger.exception("create_ticket failed for %s", user_id)
        return tool_error("internal_error", "The ticket could not be created right now.")