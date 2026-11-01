import hashlib
import json
import logging
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from common.database import execute_write, fetch_rows, find_active_employee
from common.responses import UNKNOWN_EMPLOYEE_MESSAGE, tool_error
from common.settings import settings

logger = logging.getLogger(__name__)

mcp = FastMCP("it-support-iam", host=settings.mcp_host, port=settings.iam_port, stateless_http=True, json_response=True)

EmployeeCode = Annotated[str, Field(min_length=1, max_length=32, description="Employee code of the signed-in user, supplied by the backend")]
ConversationId = Annotated[str, Field(min_length=1, max_length=64, description="Conversation id, supplied by the backend")]
ResourceName = Annotated[str, Field(min_length=2, max_length=255, description="System or resource name, for example 'Finance Shared Drive'")]
RoleName = Annotated[str, Field(min_length=2, max_length=64, description="Access role, for example READ or READ_WRITE")]
SoftwareName = Annotated[str, Field(min_length=2, max_length=128, description="Software name as listed in the catalog, for example 'Docker Desktop'")]
BusinessReason = Annotated[str, Field(min_length=10, max_length=1000, description="Why the user needs this")]

ADMIN_ROLES = ("IT_ADMIN", "SECURITY_ADMIN")
IAM_UNAVAILABLE_MESSAGE = "The identity and access system is unavailable right now."

ACTIVE_PERMISSIONS_QUERY = """
SELECT p.resource, p.role, p.granted_at
FROM itsupport.permissions p
WHERE p.employee_id = :employee_id AND p.status = 'ACTIVE'
ORDER BY p.resource
"""

RESOURCE_PERMISSIONS_QUERY = """
SELECT p.role, p.granted_at
FROM itsupport.permissions p
WHERE p.employee_id = :employee_id AND p.status = 'ACTIVE' AND LOWER(p.resource) = LOWER(:resource)
"""

OPEN_ACCESS_REQUESTS_QUERY = """
SELECT a.id AS access_request_id, a.requested_role, a.status, a.requested_at
FROM itsupport.access_requests a
WHERE a.employee_id = :employee_id AND LOWER(a.resource) = LOWER(:resource) AND a.status IN ('PENDING', 'APPROVED')
ORDER BY a.requested_at DESC
"""

SOFTWARE_SEARCH_QUERY = """
SELECT s.id AS software_id, s.name, s.vendor, s.category, s.latest_version, s.license_required, s.approval_required, s.installation_allowed
FROM itsupport.software s
WHERE s.company_id = :company_id AND s.is_active AND s.name ILIKE '%' || CAST(:software_name AS VARCHAR) || '%'
ORDER BY LENGTH(s.name)
LIMIT 5
"""

SOFTWARE_INSTALLED_ON_QUERY = """
SELECT d.hostname, i.version
FROM itsupport.installed_software i
JOIN itsupport.devices d ON d.id = i.device_id
WHERE d.employee_id = :employee_id AND i.software_id = :software_id AND i.status = 'INSTALLED'
"""

INSERT_ACCESS_REQUEST_QUERY = """
INSERT INTO itsupport.access_requests (company_id, employee_id, resource, requested_role, reason, status, idempotency_key)
VALUES (:company_id, :employee_id, :resource, :requested_role, :reason, 'PENDING', :idempotency_key)
ON CONFLICT (company_id, idempotency_key) DO NOTHING
RETURNING id AS access_request_id, resource, requested_role, status, requested_at
"""

ACCESS_REQUEST_BY_KEY_QUERY = """
SELECT a.id AS access_request_id, a.resource, a.requested_role, a.status, a.requested_at
FROM itsupport.access_requests a
WHERE a.company_id = :company_id AND a.idempotency_key = :idempotency_key
"""

EMPLOYEE_DEVICE_QUERY = """
SELECT d.id AS device_id, d.hostname
FROM itsupport.devices d
WHERE d.employee_id = :employee_id AND UPPER(d.hostname) = UPPER(:hostname)
"""

PENDING_INSTALL_APPROVAL_QUERY = """
SELECT a.id AS approval_request_id, a.status, a.created_at, a.expires_at
FROM itsupport.approval_requests a
WHERE a.requester_id = :employee_id AND a.action_type = 'SOFTWARE_INSTALL' AND a.resource_id = :software_name
  AND a.payload->>'hostname' = :hostname AND a.status = 'PENDING'
"""

INSERT_INSTALL_APPROVAL_QUERY = """
INSERT INTO itsupport.approval_requests (company_id, conversation_id, requester_id, action_type, resource_type, resource_id, payload, reason, status, expires_at)
VALUES (:company_id, :conversation_id, :employee_id, 'SOFTWARE_INSTALL', 'software', :software_name, CAST(:payload AS JSONB), :reason, 'PENDING', NOW() + INTERVAL '7 days')
RETURNING id AS approval_request_id, status, created_at, expires_at
"""

REVOKE_PERMISSION_QUERY = """
WITH revoked_permission AS (
    UPDATE itsupport.permissions
    SET status = 'REVOKED', revoked_at = NOW()
    WHERE company_id = :company_id AND employee_id = :target_employee_id AND LOWER(resource) = LOWER(:resource) AND role = :role AND status = 'ACTIVE'
    RETURNING id, resource, role, revoked_at
), audit_entry AS (
    INSERT INTO itsupport.audit_logs (company_id, user_id, action, resource_type, resource_id, details, result)
    SELECT CAST(:company_id AS BIGINT), CAST(:actor_employee_id AS BIGINT), 'REVOKE_ACCESS', 'permission', CAST(id AS VARCHAR),
           jsonb_build_object('resource', resource, 'role', role, 'target_employee_code', CAST(:target_employee_code AS VARCHAR)), 'SUCCESS'
    FROM revoked_permission
)
SELECT resource, role, revoked_at FROM revoked_permission
"""


async def find_catalog_software(company_id: int, software_name: str) -> tuple[dict | None, dict | None]:
    """Match a name against the software catalog (exact match first, then a single partial match), or return an error explaining why it can't be matched."""
    candidates = await fetch_rows(SOFTWARE_SEARCH_QUERY, {"company_id": company_id, "software_name": software_name})
    exact_matches = [software for software in candidates if software["name"].lower() == software_name.lower()]
    if exact_matches:
        return exact_matches[0], None
    if len(candidates) == 1:
        return candidates[0], None
    if not candidates:
        return None, tool_error("not_found", f"{software_name} is not in the software catalog.")
    return None, tool_error("ambiguous", f"Several catalog entries match {software_name}: {', '.join(software['name'] for software in candidates)}. Ask the user which one they mean.")


@mcp.tool()
async def get_user_permissions(employee_code: EmployeeCode) -> dict:
    """List every active permission the employee currently holds."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        permissions = await fetch_rows(ACTIVE_PERMISSIONS_QUERY, {"employee_id": employee["employee_id"]})
        return {"ok": True, "permissions": permissions}
    except Exception:
        logger.exception("get_user_permissions failed for %s", employee_code)
        return tool_error("service_unavailable", IAM_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def check_user_access(employee_code: EmployeeCode, resource: ResourceName) -> dict:
    """Check whether the employee already has access to a resource, with which roles, and whether a request for it is already open."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        lookup_parameters = {"employee_id": employee["employee_id"], "resource": resource}
        permissions = await fetch_rows(RESOURCE_PERMISSIONS_QUERY, lookup_parameters)
        open_requests = await fetch_rows(OPEN_ACCESS_REQUESTS_QUERY, lookup_parameters)
        return {"ok": True, "resource": resource, "has_access": bool(permissions), "roles": [permission["role"] for permission in permissions], "open_requests": open_requests}
    except Exception:
        logger.exception("check_user_access failed for %s", employee_code)
        return tool_error("service_unavailable", IAM_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def check_software_license(employee_code: EmployeeCode, software_name: SoftwareName) -> dict:
    """Return the catalog policy for a piece of software (license required, approval required, installation allowed) and where the employee already has it installed."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        software, error = await find_catalog_software(employee["company_id"], software_name)
        if error:
            return error
        installed_on = await fetch_rows(SOFTWARE_INSTALLED_ON_QUERY, {"employee_id": employee["employee_id"], "software_id": software.pop("software_id")})
        return {"ok": True, "software": software, "installed_on": installed_on}
    except Exception:
        logger.exception("check_software_license failed for %s", employee_code)
        return tool_error("service_unavailable", IAM_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def request_access(employee_code: EmployeeCode, conversation_id: ConversationId, resource: ResourceName, requested_role: RoleName, reason: BusinessReason) -> dict:
    """Raise a PENDING access request for the employee. It never grants access itself, and repeating it in the same conversation returns the existing request."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        current_permissions = await fetch_rows(RESOURCE_PERMISSIONS_QUERY, {"employee_id": employee["employee_id"], "resource": resource})
        if any(permission["role"] == requested_role for permission in current_permissions):
            return {"ok": True, "already_granted": True, "resource": resource, "role": requested_role}

        idempotency_key = hashlib.sha256(f"{conversation_id}|access|{resource.lower()}|{requested_role}".encode("utf-8")).hexdigest()
        request_parameters = {"company_id": employee["company_id"], "employee_id": employee["employee_id"], "resource": resource, "requested_role": requested_role, "reason": reason, "idempotency_key": idempotency_key}
        created_request = await execute_write(INSERT_ACCESS_REQUEST_QUERY, request_parameters)
        if created_request is not None:
            logger.info("Created access request %s for %s on %s", created_request["access_request_id"], employee_code, resource)
            return {"ok": True, "already_granted": False, "created": True, "access_request": created_request}

        existing_requests = await fetch_rows(ACCESS_REQUEST_BY_KEY_QUERY, {"company_id": employee["company_id"], "idempotency_key": idempotency_key})
        return {"ok": True, "already_granted": False, "created": False, "access_request": existing_requests[0]}
    except Exception:
        logger.exception("request_access failed for %s", employee_code)
        return tool_error("service_unavailable", IAM_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def request_software_installation(employee_code: EmployeeCode, conversation_id: ConversationId, software_name: SoftwareName, hostname: Annotated[str, Field(min_length=1, max_length=128, description="Hostname of the employee's device")], reason: BusinessReason) -> dict:
    """Raise a PENDING approval request to install catalog software on one of the employee's devices. Software that policy forbids is refused."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        software, error = await find_catalog_software(employee["company_id"], software_name)
        if error:
            return error
        if not software["installation_allowed"]:
            return tool_error("policy_denied", f"Company policy does not allow installing {software['name']}.")
        devices = await fetch_rows(EMPLOYEE_DEVICE_QUERY, {"employee_id": employee["employee_id"], "hostname": hostname})
        if not devices:
            return tool_error("not_found", f"No device named {hostname} is registered to this employee.")

        lookup_parameters = {"employee_id": employee["employee_id"], "software_name": software["name"], "hostname": devices[0]["hostname"]}
        pending_approvals = await fetch_rows(PENDING_INSTALL_APPROVAL_QUERY, lookup_parameters)
        if pending_approvals:
            return {"ok": True, "created": False, "approval_request": pending_approvals[0]}

        payload = json.dumps({"software": software["name"], "version": software["latest_version"], "hostname": devices[0]["hostname"], "device_id": devices[0]["device_id"]})
        approval_parameters = {"company_id": employee["company_id"], "conversation_id": conversation_id, "employee_id": employee["employee_id"], "software_name": software["name"], "payload": payload, "reason": reason}
        created_approval = await execute_write(INSERT_INSTALL_APPROVAL_QUERY, approval_parameters)
        logger.info("Created install approval %s for %s on %s", created_approval["approval_request_id"], software["name"], devices[0]["hostname"])
        return {"ok": True, "created": True, "approval_required": software["approval_required"], "approval_request": created_approval}
    except Exception:
        logger.exception("request_software_installation failed for %s", employee_code)
        return tool_error("service_unavailable", IAM_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def revoke_access(employee_code: EmployeeCode, target_employee_code: Annotated[str, Field(min_length=1, max_length=32, description="Employee whose access is revoked")], resource: ResourceName, role: RoleName) -> dict:
    """Revoke an active permission. Only IT_ADMIN or SECURITY_ADMIN callers may do this, and every revocation is written to the audit log."""
    try:
        actor = await find_active_employee(employee_code)
        if actor is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        if actor["role"] not in ADMIN_ROLES:
            logger.warning("Denied revoke_access for %s with role %s", employee_code, actor["role"])
            return tool_error("unauthorized", "Only IT or security administrators can revoke access.")
        target_employee = await find_active_employee(target_employee_code)
        if target_employee is None or target_employee["company_id"] != actor["company_id"]:
            return tool_error("not_found", f"No active employee {target_employee_code} exists in this company.")

        revoke_parameters = {"company_id": actor["company_id"], "actor_employee_id": actor["employee_id"], "target_employee_id": target_employee["employee_id"], "target_employee_code": target_employee_code, "resource": resource, "role": role}
        revoked_permission = await execute_write(REVOKE_PERMISSION_QUERY, revoke_parameters)
        if revoked_permission is None:
            return tool_error("not_found", f"{target_employee_code} has no active {role} permission on {resource}.")
        logger.info("%s revoked %s on %s from %s", employee_code, role, resource, target_employee_code)
        return {"ok": True, "revoked": revoked_permission}
    except Exception:
        logger.exception("revoke_access failed for %s", employee_code)
        return tool_error("service_unavailable", IAM_UNAVAILABLE_MESSAGE, retryable=True)


if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mcp.run(transport="streamable-http")