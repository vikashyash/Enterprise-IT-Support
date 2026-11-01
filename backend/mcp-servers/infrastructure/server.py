import logging
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from common.database import fetch_rows, find_active_employee
from common.responses import UNKNOWN_EMPLOYEE_MESSAGE, tool_error
from common.settings import settings

logger = logging.getLogger(__name__)

mcp = FastMCP("it-support-infrastructure", host=settings.mcp_host, port=settings.infrastructure_port, stateless_http=True, json_response=True)

EmployeeCode = Annotated[str, Field(min_length=1, max_length=32, description="Employee code of the signed-in user, supplied by the backend")]
ServiceName = Literal["VPN", "Microsoft 365", "Outlook", "Teams", "GitHub Enterprise", "DNS", "SSO", "Active Directory", "File Storage"]

SERVICES_QUERY = """
SELECT s.name, s.service_type, s.status, s.health, s.description, s.last_checked_at
FROM itsupport.services s
WHERE s.company_id = :company_id AND s.name = ANY(:service_names)
ORDER BY s.name
"""

ACTIVE_INCIDENTS_QUERY = """
SELECT i.incident_number, i.title, i.severity, i.status, i.started_at, s.name AS service_name
FROM itsupport.incidents i
JOIN itsupport.services s ON s.id = i.affected_service_id
WHERE i.company_id = :company_id
  AND i.status <> 'RESOLVED'
  AND (CAST(:service_names AS VARCHAR[]) IS NULL OR s.name = ANY(CAST(:service_names AS VARCHAR[])))
ORDER BY i.severity, i.started_at DESC
"""


async def read_service_health(employee_code: str, service_names: list[str]) -> dict:
    """Return status, health and active incidents for the named services in the employee's company; shared body of every check_* tool."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        services = await fetch_rows(SERVICES_QUERY, {"company_id": employee["company_id"], "service_names": service_names})
        if not services:
            return tool_error("not_found", f"No services named {', '.join(service_names)} are registered in the service catalog.")
        active_incidents = await fetch_rows(ACTIVE_INCIDENTS_QUERY, {"company_id": employee["company_id"], "service_names": service_names})
        all_operational = all(service["status"] == "OPERATIONAL" for service in services) and not active_incidents
        return {"ok": True, "all_operational": all_operational, "services": services, "active_incidents": active_incidents}
    except Exception:
        logger.exception("Service health check failed for %s", service_names)
        return tool_error("service_unavailable", "Service health could not be checked right now.", retryable=True)


@mcp.tool()
async def check_service_health(employee_code: EmployeeCode, service_name: ServiceName) -> dict:
    """Check the status, health and active incidents of one enterprise IT service."""
    return await read_service_health(employee_code, [service_name])


@mcp.tool()
async def check_vpn_status(employee_code: EmployeeCode) -> dict:
    """Check the corporate VPN service and its active incidents. Call this before troubleshooting the user's device for VPN problems."""
    return await read_service_health(employee_code, ["VPN"])


@mcp.tool()
async def check_network_status(employee_code: EmployeeCode) -> dict:
    """Check the core corporate network services (DNS and VPN) and their active incidents."""
    return await read_service_health(employee_code, ["DNS", "VPN"])


@mcp.tool()
async def check_dns_status(employee_code: EmployeeCode) -> dict:
    """Check the internal DNS service and its active incidents."""
    return await read_service_health(employee_code, ["DNS"])


@mcp.tool()
async def check_sso_status(employee_code: EmployeeCode) -> dict:
    """Check single sign-on and Active Directory, which most login problems depend on."""
    return await read_service_health(employee_code, ["SSO", "Active Directory"])


@mcp.tool()
async def check_email_service(employee_code: EmployeeCode) -> dict:
    """Check Outlook and Microsoft 365, which email sync problems depend on."""
    return await read_service_health(employee_code, ["Outlook", "Microsoft 365"])


@mcp.tool()
async def search_active_incidents(employee_code: EmployeeCode, service_name: ServiceName | None = None) -> dict:
    """List unresolved incidents in the company, optionally only for one service. Use it to tell the user about known outages."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        service_names = [service_name] if service_name else None
        active_incidents = await fetch_rows(ACTIVE_INCIDENTS_QUERY, {"company_id": employee["company_id"], "service_names": service_names})
        return {"ok": True, "active_incidents": active_incidents}
    except Exception:
        logger.exception("search_active_incidents failed for %s", employee_code)
        return tool_error("service_unavailable", "Incident data is unavailable right now.", retryable=True)


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mcp.run(transport="streamable-http")