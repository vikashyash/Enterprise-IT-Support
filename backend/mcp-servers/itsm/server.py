import hashlib
import logging
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from common.database import execute_write, fetch_rows, find_active_employee
from common.responses import UNKNOWN_EMPLOYEE_MESSAGE, tool_error
from common.settings import settings

logger = logging.getLogger(__name__)

mcp = FastMCP("it-support-itsm", host=settings.mcp_host, port=settings.itsm_port, stateless_http=True, json_response=True)

EmployeeCode = Annotated[str, Field(min_length=1, max_length=32, description="Employee code of the signed-in user, supplied by the backend")]
ConversationId = Annotated[str, Field(min_length=1, max_length=64, description="Conversation id, supplied by the backend")]
TicketNumber = Annotated[str, Field(pattern=r"^INC-\d+$", description="Ticket number, for example INC-100123")]
TicketTitle = Annotated[str, Field(min_length=5, max_length=200, description="Short summary, for example 'VPN disconnects every few minutes'")]
TicketDescription = Annotated[str, Field(min_length=10, max_length=4000, description="What the user reported and what has already been checked")]
TicketCategory = Annotated[Literal["network", "email", "hardware", "software", "access", "security", "general"], Field(description="IT area the issue belongs to")]
TicketPriority = Annotated[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"], Field(description="Business impact of the issue")]
TicketStatus = Literal["OPEN", "IN_PROGRESS", "WAITING_ON_USER", "WAITING_ON_APPROVAL", "RESOLVED", "CLOSED", "CANCELLED"]
ResultLimit = Annotated[int, Field(ge=1, le=20, description="Maximum number of results")]

CATEGORY_TEAMS = {"network": "Network", "email": "Collaboration", "hardware": "EndUserSupport", "software": "EndUserSupport", "access": "IdentityAccess", "security": "Security", "general": "ServiceDesk"}
TICKETING_UNAVAILABLE_MESSAGE = "The ticketing system is unavailable right now."

INSERT_TICKET_QUERY = """
WITH new_ticket AS (SELECT nextval(pg_get_serial_sequence('itsupport.tickets', 'id')) AS id)
INSERT INTO itsupport.tickets (id, ticket_number, company_id, employee_id, title, description, category, priority, status, assigned_team, idempotency_key)
VALUES ((SELECT id FROM new_ticket), (SELECT 'INC-' || (100000 + id) FROM new_ticket), :company_id, :employee_id, :title, :description, :category, :priority, 'OPEN', :assigned_team, :idempotency_key)
ON CONFLICT (company_id, idempotency_key) DO NOTHING
RETURNING id AS ticket_id, ticket_number, title, category, priority, status, assigned_team, created_at
"""

TICKET_BY_IDEMPOTENCY_KEY_QUERY = """
SELECT t.id AS ticket_id, t.ticket_number, t.title, t.category, t.priority, t.status, t.assigned_team, t.created_at
FROM itsupport.tickets t
WHERE t.company_id = :company_id AND t.idempotency_key = :idempotency_key
"""

TICKET_BY_NUMBER_QUERY = """
SELECT t.id AS ticket_id, t.ticket_number, t.title, t.description, t.category, t.priority, t.status, t.assigned_team, t.created_at, t.updated_at, t.resolved_at
FROM itsupport.tickets t
WHERE t.employee_id = :employee_id AND t.ticket_number = :ticket_number
"""

TICKET_COMMENTS_QUERY = """
SELECT c.author_type, c.comment, c.created_at
FROM itsupport.ticket_comments c
WHERE c.ticket_id = :ticket_id AND c.is_internal = FALSE
ORDER BY c.created_at
"""

SEARCH_TICKETS_QUERY = """
SELECT t.ticket_number, t.title, t.category, t.priority, t.status, t.created_at
FROM itsupport.tickets t
WHERE t.employee_id = :employee_id AND (CAST(:status AS VARCHAR) IS NULL OR t.status::text = CAST(:status AS VARCHAR))
ORDER BY t.created_at DESC
LIMIT :result_limit
"""

UPDATE_TICKET_QUERY = """
UPDATE itsupport.tickets
SET priority = COALESCE(CAST(:priority AS itsupport.ticket_priority), priority), title = COALESCE(CAST(:title AS VARCHAR), title)
WHERE employee_id = :employee_id AND ticket_number = :ticket_number AND status NOT IN ('RESOLVED', 'CLOSED', 'CANCELLED')
RETURNING id AS ticket_id, ticket_number, title, priority, status, updated_at
"""

INSERT_COMMENT_QUERY = """
INSERT INTO itsupport.ticket_comments (ticket_id, author_type, author_id, comment, is_internal)
SELECT t.id, CAST('EMPLOYEE' AS itsupport.author_type), t.employee_id, CAST(:comment AS TEXT), FALSE
FROM itsupport.tickets t
WHERE t.employee_id = :employee_id AND t.ticket_number = :ticket_number
RETURNING id AS comment_id, created_at
"""

CLOSE_TICKET_QUERY = """
WITH closed_ticket AS (
    UPDATE itsupport.tickets
    SET status = 'CLOSED', resolved_at = NOW()
    WHERE employee_id = :employee_id AND ticket_number = :ticket_number AND status NOT IN ('CLOSED', 'CANCELLED')
    RETURNING id, employee_id, ticket_number, status, resolved_at
), resolution_note AS (
    INSERT INTO itsupport.ticket_comments (ticket_id, author_type, author_id, comment, is_internal)
    SELECT id, CAST('EMPLOYEE' AS itsupport.author_type), employee_id, CAST(:resolution_note AS TEXT), FALSE
    FROM closed_ticket
)
SELECT id AS ticket_id, ticket_number, status, resolved_at FROM closed_ticket
"""

SEARCH_INCIDENTS_QUERY = """
SELECT i.incident_number, i.title, i.severity, i.status, i.started_at, i.resolved_at, s.name AS service_name
FROM itsupport.incidents i
LEFT JOIN itsupport.services s ON s.id = i.affected_service_id
WHERE i.company_id = :company_id
  AND (CAST(:include_resolved AS BOOLEAN) OR i.status <> 'RESOLVED')
  AND (CAST(:keyword AS VARCHAR) IS NULL
       OR i.title ILIKE '%' || CAST(:keyword AS VARCHAR) || '%'
       OR i.description ILIKE '%' || CAST(:keyword AS VARCHAR) || '%'
       OR s.name ILIKE '%' || CAST(:keyword AS VARCHAR) || '%')
ORDER BY i.started_at DESC
LIMIT :result_limit
"""

INCIDENT_BY_NUMBER_QUERY = """
SELECT i.incident_number, i.title, i.description, i.severity, i.status, i.started_at, i.resolved_at, s.name AS service_name
FROM itsupport.incidents i
LEFT JOIN itsupport.services s ON s.id = i.affected_service_id
WHERE i.company_id = :company_id AND i.incident_number = :incident_number
"""


@mcp.tool()
async def create_ticket(employee_code: EmployeeCode, conversation_id: ConversationId, title: TicketTitle, description: TicketDescription, category: TicketCategory, priority: TicketPriority = "MEDIUM") -> dict:
    """Open an IT support ticket for the employee. Calling it again for the same category in the same conversation returns the existing ticket instead of a duplicate."""
    try:
        employee = await find_active_employee(employee_code)
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
            logger.info("Created ticket %s for %s", created_ticket["ticket_number"], employee_code)
            return {"ok": True, "created": True, "ticket": created_ticket}

        existing_tickets = await fetch_rows(TICKET_BY_IDEMPOTENCY_KEY_QUERY, {"company_id": employee["company_id"], "idempotency_key": idempotency_key})
        return {"ok": True, "created": False, "ticket": existing_tickets[0]}
    except Exception:
        logger.exception("create_ticket failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def get_ticket(employee_code: EmployeeCode, ticket_number: TicketNumber) -> dict:
    """Return one of the employee's tickets with its current status and public comments."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        tickets = await fetch_rows(TICKET_BY_NUMBER_QUERY, {"employee_id": employee["employee_id"], "ticket_number": ticket_number})
        if not tickets:
            return tool_error("not_found", f"Ticket {ticket_number} was not found among this employee's tickets.")
        comments = await fetch_rows(TICKET_COMMENTS_QUERY, {"ticket_id": tickets[0]["ticket_id"]})
        return {"ok": True, "ticket": tickets[0], "comments": comments}
    except Exception:
        logger.exception("get_ticket failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def search_tickets(employee_code: EmployeeCode, status: TicketStatus | None = None, result_limit: ResultLimit = 10) -> dict:
    """List the employee's tickets, newest first, optionally filtered by status."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        tickets = await fetch_rows(SEARCH_TICKETS_QUERY, {"employee_id": employee["employee_id"], "status": status, "result_limit": result_limit})
        return {"ok": True, "tickets": tickets}
    except Exception:
        logger.exception("search_tickets failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def update_ticket(employee_code: EmployeeCode, ticket_number: TicketNumber, priority: TicketPriority | None = None, title: TicketTitle | None = None) -> dict:
    """Change the priority or title of one of the employee's open tickets."""
    try:
        if priority is None and title is None:
            return tool_error("invalid_input", "Provide a new priority or a new title to update the ticket.")
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        updated_ticket = await execute_write(UPDATE_TICKET_QUERY, {"employee_id": employee["employee_id"], "ticket_number": ticket_number, "priority": priority, "title": title})
        if updated_ticket is None:
            return tool_error("not_found", f"Ticket {ticket_number} was not found or is already closed.")
        return {"ok": True, "ticket": updated_ticket}
    except Exception:
        logger.exception("update_ticket failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def add_ticket_comment(employee_code: EmployeeCode, ticket_number: TicketNumber, comment: Annotated[str, Field(min_length=2, max_length=2000, description="Note to add on the user's behalf")]) -> dict:
    """Add a note to one of the employee's tickets, for example 'I already restarted my laptop'."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        added_comment = await execute_write(INSERT_COMMENT_QUERY, {"employee_id": employee["employee_id"], "ticket_number": ticket_number, "comment": comment})
        if added_comment is None:
            return tool_error("not_found", f"Ticket {ticket_number} was not found among this employee's tickets.")
        return {"ok": True, "ticket_number": ticket_number, "comment": added_comment}
    except Exception:
        logger.exception("add_ticket_comment failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def close_ticket(employee_code: EmployeeCode, ticket_number: TicketNumber, resolution_note: Annotated[str, Field(min_length=5, max_length=2000, description="Why the ticket can be closed, in the user's words")]) -> dict:
    """Close one of the employee's tickets with a resolution note. Closing an already closed ticket is reported, not repeated."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        closed_ticket = await execute_write(CLOSE_TICKET_QUERY, {"employee_id": employee["employee_id"], "ticket_number": ticket_number, "resolution_note": resolution_note})
        if closed_ticket is not None:
            return {"ok": True, "already_closed": False, "ticket": closed_ticket}

        existing_tickets = await fetch_rows(TICKET_BY_NUMBER_QUERY, {"employee_id": employee["employee_id"], "ticket_number": ticket_number})
        if not existing_tickets:
            return tool_error("not_found", f"Ticket {ticket_number} was not found among this employee's tickets.")
        if existing_tickets[0]["status"] == "CLOSED":
            return {"ok": True, "already_closed": True, "ticket": existing_tickets[0]}
        return tool_error("invalid_state", f"Ticket {ticket_number} is {existing_tickets[0]['status']} and cannot be closed.")
    except Exception:
        logger.exception("close_ticket failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def search_incidents(employee_code: EmployeeCode, keyword: Annotated[str | None, Field(max_length=100, description="Word to match in title, description or service name")] = None, include_resolved: bool = False, result_limit: ResultLimit = 10) -> dict:
    """Search the company's incidents by keyword; unresolved incidents only unless include_resolved is true."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        incidents = await fetch_rows(SEARCH_INCIDENTS_QUERY, {"company_id": employee["company_id"], "keyword": keyword, "include_resolved": include_resolved, "result_limit": result_limit})
        return {"ok": True, "incidents": incidents}
    except Exception:
        logger.exception("search_incidents failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def get_incident(employee_code: EmployeeCode, incident_number: Annotated[str, Field(pattern=r"^INC-\d+$", description="Incident number, for example INC-900101")]) -> dict:
    """Return the details and current status of one company incident."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        incidents = await fetch_rows(INCIDENT_BY_NUMBER_QUERY, {"company_id": employee["company_id"], "incident_number": incident_number})
        if not incidents:
            return tool_error("not_found", f"Incident {incident_number} was not found.")
        return {"ok": True, "incident": incidents[0]}
    except Exception:
        logger.exception("get_incident failed for %s", employee_code)
        return tool_error("service_unavailable", TICKETING_UNAVAILABLE_MESSAGE, retryable=True)


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mcp.run(transport="streamable-http")