import logging
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from common.database import fetch_rows, find_active_employee
from common.responses import UNKNOWN_EMPLOYEE_MESSAGE, tool_error
from common.settings import settings

logger = logging.getLogger(__name__)

mcp=FastMCP("it-support-device",host=settings.mcp_host,port=settings.device_port,stateless_http=True, json_response=True)

EmployeeCode = Annotated[str, Field(min_length=1, max_length=32, description="Employee code of the signed-in user, supplied by the backend")]
Hostname = Annotated[str | None, Field(max_length=128, description="Device hostname; omit to use the employee's primary device")]

ONLINE_WINDOW_MINUTES = 15
LOW_STORAGE_PERCENT = 90
INVENTORY_UNAVAILABLE_MESSAGE = "The device inventory is unavailable right now."
SIMULATED_TOP_PROCESSES = {
    "Windows": [{"name": "MsMpEng.exe", "cpu_percent": 21.4}, {"name": "OneDrive.exe", "cpu_percent": 12.8}, {"name": "ms-teams.exe", "cpu_percent": 9.6}],
    "macOS": [{"name": "mds_stores", "cpu_percent": 18.2}, {"name": "Microsoft Teams", "cpu_percent": 11.5}, {"name": "Google Chrome Helper", "cpu_percent": 8.7}],
}

EMPLOYEE_DEVICES_QUERY = """
SELECT d.id AS device_id, d.asset_tag, d.hostname, d.device_type, d.manufacturer, d.model, d.operating_system, d.os_version, d.cpu, d.ram_gb,
       d.storage_total_gb, d.storage_free_gb,
       ROUND(100.0 * (d.storage_total_gb - d.storage_free_gb) / NULLIF(d.storage_total_gb, 0), 1)::float AS storage_used_percent,
       host(d.ip_address) AS ip_address, d.mac_address::text AS mac_address, d.last_seen_at,
       COALESCE(d.last_seen_at >= NOW() - make_interval(mins => :online_window_minutes), FALSE) AS is_online,
       d.status
FROM itsupport.devices d
WHERE d.employee_id = :employee_id
ORDER BY (d.status = 'ACTIVE') DESC, d.last_seen_at DESC NULLS LAST
"""

INSTALLED_SOFTWARE_QUERY = """
SELECT s.name, s.vendor, s.category, i.version AS installed_version, s.latest_version,
       (i.version IS DISTINCT FROM s.latest_version) AS update_available, i.status
FROM itsupport.installed_software i
JOIN itsupport.software s ON s.id = i.software_id
WHERE i.device_id = :device_id
ORDER BY s.name
"""

async def find_employee_device(employee_code:str,host_name:str|None)->tuple[dict|None,dict|None]:
    """Return (device, None) for the employee's named or primary device, or (None, error) when the employee or device is unknown."""
    employee=await find_active_employee(employee_code=employee_code)
    if employee is None:
        return None, tool_error(error_type="not_found",message=UNKNOWN_EMPLOYEE_MESSAGE)
    devices = await fetch_rows(EMPLOYEE_DEVICES_QUERY, {"employee_id": employee["employee_id"], "online_window_minutes": ONLINE_WINDOW_MINUTES})
    if host_name:
        devices = [device for device in devices if device["hostname"].upper() == host_name.upper()]
    if not devices:
        return None, tool_error("not_found", f"No device named {host_name} is registered to this employee." if host_name else "No devices are registered to this employee.")
    return devices[0], None


@mcp.tool()
async def get_employee(employee_code:EmployeeCode)->dict:
    """Look up the signed-in employee: name, email, job title, department, role and status."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        return {"ok": True, "employee": {key: value for key, value in employee.items() if key not in ("employee_id", "company_id")}}
    except Exception:
        logger.exception("get_employee failed for %s", employee_code)
        return tool_error("service_unavailable", "The employee directory is unavailable right now.", retryable=True)

@mcp.tool()
async def get_employee_devices(employee_code: EmployeeCode) -> dict:
    """List every device registered to the employee with type, model, OS, status and whether it is online. The first one is the primary device."""
    try:
        employee = await find_active_employee(employee_code)
        if employee is None:
            return tool_error("not_found", UNKNOWN_EMPLOYEE_MESSAGE)
        devices = await fetch_rows(EMPLOYEE_DEVICES_QUERY, {"employee_id": employee["employee_id"], "online_window_minutes": ONLINE_WINDOW_MINUTES})
        summary_fields = ("hostname", "device_type", "manufacturer", "model", "operating_system", "os_version", "status", "is_online", "last_seen_at")
        return {"ok": True, "devices": [{field: device[field] for field in summary_fields} for device in devices]}
    except Exception:
        logger.exception("get_employee_devices failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)

    
@mcp.tool()
async def get_device(employee_code: EmployeeCode, hostname: Hostname = None) -> dict:
    """Return full details of one of the employee's devices: hardware, OS, storage, IP address, status and last check-in."""
    try:
        device, error = await find_employee_device(employee_code, hostname)
        if error:
            return error
        device.pop("device_id")
        return {"ok": True, "device": device}
    except Exception:
        logger.exception("get_device failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def get_device_status(employee_code: EmployeeCode, hostname: Hostname = None) -> dict:
    """Return whether the employee's device is active, currently online, and when it last checked in."""
    try:
        device, error = await find_employee_device(employee_code, hostname)
        if error:
            return error
        return {"ok": True, "hostname": device["hostname"], "status": device["status"], "is_online": device["is_online"], "last_seen_at": device["last_seen_at"]}
    except Exception:
        logger.exception("get_device_status failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)


@mcp.tool()
async def get_device_network_info(employee_code: EmployeeCode, hostname: Hostname = None) -> dict:
    """Return the device's network details: IP address, MAC address and whether it is reachable on the corporate network."""
    try:
        device, error = await find_employee_device(employee_code, hostname)
        if error:
            return error
        return {"ok": True, "hostname": device["hostname"], "ip_address": device["ip_address"], "mac_address": device["mac_address"], "network_reachable": device["is_online"], "last_seen_at": device["last_seen_at"]}
    except Exception:
        logger.exception("get_device_network_info failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)
    
@mcp.tool()
async def get_installed_software(employee_code: EmployeeCode, hostname: Hostname = None) -> dict:
    """List software installed on the device with installed vs latest version, so outdated clients (for example the VPN client) can be spotted."""
    try:
        device, error = await find_employee_device(employee_code, hostname)
        if error:
            return error
        installed_software = await fetch_rows(INSTALLED_SOFTWARE_QUERY, {"device_id": device["device_id"]})
        return {"ok": True, "hostname": device["hostname"], "software": installed_software}
    except Exception:
        logger.exception("get_installed_software failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)

    
@mcp.tool()
async def get_device_storage(employee_code: EmployeeCode, hostname: Hostname = None) -> dict:
    """Report the device's total and free storage, percentage used, and whether storage is critically low."""
    try:
        device, error = await find_employee_device(employee_code, hostname)
        if error:
            return error
        used_percent = device["storage_used_percent"] or 0.0
        return {"ok": True, "hostname": device["hostname"], "storage_total_gb": device["storage_total_gb"], "storage_free_gb": device["storage_free_gb"], "storage_used_percent": used_percent, "is_low_storage": used_percent >= LOW_STORAGE_PERCENT}
    except Exception:
        logger.exception("get_device_storage failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)

    
@mcp.tool()
async def get_device_performance(employee_code: EmployeeCode, hostname: Hostname = None) -> dict:
    """Return current CPU, memory and disk usage plus the top processes. Values are simulated from inventory data until a real endpoint agent exists."""
    try:
        device, error = await find_employee_device(employee_code, hostname)
        if error:
            return error
        disk_percent = device["storage_used_percent"] or 0.0
        memory_percent = 91.2 if (device["ram_gb"] or 0) <= 16 else 54.0
        cpu_percent = 87.3 if disk_percent >= LOW_STORAGE_PERCENT else 32.5
        top_processes = SIMULATED_TOP_PROCESSES.get(device["operating_system"], [])
        return {"ok": True, "simulated": True, "hostname": device["hostname"], "cpu_percent": cpu_percent, "memory_percent": memory_percent, "disk_percent": disk_percent, "top_processes": top_processes}
    except Exception:
        logger.exception("get_device_performance failed for %s", employee_code)
        return tool_error("service_unavailable", INVENTORY_UNAVAILABLE_MESSAGE, retryable=True)

    
if __name__ == "__main__":
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mcp.run(transport="streamable-http")
    
    