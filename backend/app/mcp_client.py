import asyncio
import json
import logging

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool,ToolException
from langchain_mcp_adapters.client import MultiServerMCPClient
from app.config import settings

logger = logging.getLogger(__name__)

MCP_SERVERS={
    "itsm":{"url":settings.mcp_itsm_url,"transport":"streamable_http"},
    "device": {"url": settings.mcp_device_url, "transport": "streamable_http"},
    "infrastructure": {"url": settings.mcp_infrastructure_url, "transport": "streamable_http"},
    "iam": {"url": settings.mcp_iam_url, "transport": "streamable_http"},
}

TRUSTED_ARGUMENTS = ("employee_code", "conversation_id")

mcp_client=MultiServerMCPClient(MCP_SERVERS)
available_tools:dict[str,BaseTool]={}
connected_servers:list[str]=[]

async def load_mcp_tools() -> None:
    """Discover the tools of every MCP server. A server that is down is logged and skipped so the API can still start."""
    available_tools.clear()
    connected_servers.clear()
    for server_name in MCP_SERVERS:
        try:
            server_tools = await mcp_client.get_tools(server_name=server_name)
        except Exception:
            logger.exception("MCP server %s is unavailable; its tools are disabled", server_name)
            continue
        connected_servers.append(server_name)
        available_tools.update({server_tool.name: server_tool for server_tool in server_tools})
    logger.info("Loaded %d MCP tools from %s", len(available_tools), connected_servers)

def read_input_schema(mcp_tool: BaseTool) -> dict:
    """Return a tool's JSON input schema, whether it is stored as a plain dict (MCP tools) or as a Pydantic model."""
    return mcp_tool.args_schema if isinstance(mcp_tool.args_schema, dict) else mcp_tool.args_schema.model_json_schema()

def build_llm_tool_specs(tool_names: list[str]) -> list[dict]:
    """Describe the allowed, currently available tools to the LLM, hiding the trusted arguments the backend fills in itself."""
    tool_specs = []
    for tool_name in tool_names:
        mcp_tool = available_tools.get(tool_name)
        if mcp_tool is None:
            continue
        input_schema = read_input_schema(mcp_tool)
        llm_properties = {}
        for property_name, property_schema in input_schema.get("properties", {}).items():
            if property_name in TRUSTED_ARGUMENTS:
                continue
            # Gemini cannot read "anyOf [type, null]" for optional arguments, so expose the non-null type only.
            non_null_options = [option for option in property_schema.get("anyOf", []) if option.get("type") != "null"]
            llm_properties[property_name] = {**non_null_options[0], "description": property_schema.get("description", "")} if len(non_null_options) == 1 else property_schema
        required_properties = [property_name for property_name in input_schema.get("required", []) if property_name not in TRUSTED_ARGUMENTS]
        tool_specs.append({"name": tool_name, "description": mcp_tool.description, "parameters": {"type": "object", "properties": llm_properties, "required": required_properties}})
    return tool_specs

def build_tool_error_message(tool_call: dict, error_type: str, message: str, retryable: bool = False) -> ToolMessage:
    """Wrap a failed tool call in a ToolMessage the agent can read, using the same {"ok": false} shape the MCP tools return."""
    error_payload = {"ok": False, "error": {"type": error_type, "message": message, "retryable": retryable}}
    return ToolMessage(content=json.dumps(error_payload), name=tool_call["name"], tool_call_id=tool_call["id"], status="error")

async def call_mcp_tool(tool_call: dict, trusted_arguments: dict, allowed_tool_names: list[str]) -> ToolMessage:
    """Run one LLM tool call on its MCP server: enforce the allow-list, overwrite trusted arguments, apply a timeout, and never raise."""
    tool_name = tool_call["name"]
    if tool_name not in allowed_tool_names:
        logger.warning("Blocked tool call %s: not allowed for this request", tool_name)
        return build_tool_error_message(tool_call, "not_allowed", f"The tool {tool_name} is not available for this request.")
    mcp_tool = available_tools.get(tool_name)
    if mcp_tool is None:
        return build_tool_error_message(tool_call, "service_unavailable", f"The system behind {tool_name} is currently unavailable.", retryable=True)
    accepted_arguments = read_input_schema(mcp_tool).get("properties", {})
    tool_arguments = {**tool_call["args"], **{name: value for name, value in trusted_arguments.items() if name in accepted_arguments}}
    try:
        tool_result = await asyncio.wait_for(mcp_tool.ainvoke(tool_arguments), timeout=settings.mcp_tool_timeout_seconds)
    except TimeoutError:
        logger.warning("MCP tool %s timed out after %ss", tool_name, settings.mcp_tool_timeout_seconds)
        return build_tool_error_message(tool_call, "timeout", f"{tool_name} did not respond in time.", retryable=True)
    except ToolException as error:
        return build_tool_error_message(tool_call, "tool_error", str(error))
    except Exception:
        logger.exception("MCP tool %s failed", tool_name)
        return build_tool_error_message(tool_call, "service_unavailable", f"The system behind {tool_name} is currently unavailable.", retryable=True)
    tool_output = tool_result if isinstance(tool_result, str) else "".join(block if isinstance(block, str) else block.get("text", "") for block in tool_result)
    return ToolMessage(content=tool_output, name=tool_name, tool_call_id=tool_call["id"])