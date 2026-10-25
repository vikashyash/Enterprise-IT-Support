import asyncio
import logging
from typing import Literal

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import tools_condition
from langgraph.types import interrupt

from app.config import settings
from app.llm import get_chat_model
from app.mcp_client import build_llm_tool_specs, call_mcp_tool
from app.schema import Intent, RequestUnderstanding
from app.state import SupportState

logger = logging.getLogger(__name__)

TOOLS_BY_INTENT = {
    Intent.TROUBLESHOOTING.value: [
        "get_employee", "get_employee_devices", "get_device", "get_device_status", "get_device_network_info", "get_installed_software", "get_device_storage", "get_device_performance",
        "check_service_health", "check_vpn_status", "check_network_status", "check_dns_status", "check_sso_status", "check_email_service", "search_active_incidents",
        "create_ticket", "search_tickets",
    ],
    Intent.TICKET_REQUEST.value: [
        "create_ticket", "get_ticket", "search_tickets", "update_ticket", "add_ticket_comment", "close_ticket", "search_incidents", "get_incident", "get_employee_devices",
    ],
}

UNDERSTANDING_SYSTEM_PROMPT = """You are the request-understanding step of an enterprise IT support agent.
Read the whole conversation and describe the user's latest request as structured data.

Intents:
- knowledge: the user wants information, how-to steps or company IT policy.
- troubleshooting: something is broken or behaving badly (VPN, email, slow laptop, network, applications).
- access_request: the user needs access to a system, application, shared drive or permission.
- software_request: the user wants software installed, updated or licensed.
- security_issue: suspicious logins, unexpected MFA prompts, phishing or a compromised account.
- ticket_request: the user explicitly asks to create, check or update an IT ticket.
- unknown: not an IT support request, or too unclear to classify.

Rules:
- missing_information lists only details that are critical to act and that IT systems cannot look up, such as which application to install or which resource to access.
- Never ask for the user's employee ID, email or device details; the system already knows who the user is.
- Use earlier turns: if the user already answered a question, do not list it as missing again.
- clarifying_question is one short, polite question covering everything in missing_information, otherwise null.
- is_sensitive_action is true for password resets, access grants or revokes, software installation, account or security changes.
- confidence reflects how sure you are about the intent, from 0.0 to 1.0."""

RESPONSE_SYSTEM_PROMPT = """You are an enterprise IT support assistant replying to an employee.
Request type: {intent}
Request summary: {issue_summary}
Planned next step: {next_step}
Still missing from the user: {missing_information}

Write 2 to 3 short sentences that acknowledge the request and explain the planned next step.
If details are still missing, say which ones are needed to continue.
Do not claim you have already checked any system or performed any action.
Do not invent company policies, ticket numbers or system status."""

AGENT_SYSTEM_PROMPT = """You are an enterprise IT support agent helping an employee.
Request type: {intent}
Request summary: {issue_summary}

Your tools cover the employee's profile, their devices (status, network, storage, performance, installed software), enterprise service health and incidents, and IT tickets.
How to work:
- Call only the tools you need and read each result before deciding the next step.
- The tools already know who the employee is; never ask for or invent employee IDs.
- For service problems (VPN, email, SSO, DNS), check the service first. If it has an active incident, tell the user and do not troubleshoot their device.
- If a tool returns ok=false, do not guess the missing data; say what could not be checked.
- Create a ticket only when the user asks for one or the issue cannot be resolved with the information available.
- Finish with 2 to 4 short sentences: what you checked, what you found and the next step. Quote ticket and incident numbers exactly as returned.
- Never claim an action was performed unless a tool performed it."""

INTENT_NEXT_STEPS = {
    Intent.KNOWLEDGE: "I'll look this up in the internal IT knowledge base and answer with sources.",
    Intent.TROUBLESHOOTING: "I'll check your device and the related IT services to find the cause.",
    Intent.ACCESS_REQUEST: "I'll check your current access and the access policy, then raise a request for approval.",
    Intent.SOFTWARE_REQUEST: "I'll check the software policy, licensing and whether approval is needed before installation.",
    Intent.SECURITY_ISSUE: "I'll treat this as a priority security concern and route it to the security workflow.",
    Intent.TICKET_REQUEST: "I'll create an IT ticket with the details you've provided.",
}

UNKNOWN_REQUEST_MESSAGE = "I can help with IT issues such as VPN, email, device problems, software, access requests, security concerns and tickets. Could you describe what you need in a bit more detail?"
TOOL_LIMIT_MESSAGE = "I ran the checks I could but couldn't finish the investigation automatically. I recommend raising an IT ticket so a technician can follow up."
AGENT_FAILURE_MESSAGE = "I couldn't complete the checks right now. Please try again in a few minutes, or ask me to raise an IT ticket."
SYSTEMS_UNAVAILABLE_MESSAGE = "The IT systems I need to check this are unavailable right now. Please try again shortly, or contact the service desk directly."


def select_conversation_messages(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Keep only the user and assistant chat turns, dropping tool calls and tool results that the understanding and reply steps don't need."""
    return [message for message in messages if isinstance(message, HumanMessage) or (isinstance(message, AIMessage) and not message.tool_calls)]


def read_message_text(message: AIMessage) -> str:
    """Return the plain text of an LLM reply, whether the provider sent a string or a list of content blocks."""
    if isinstance(message.content, str):
        return message.content.strip()
    return "".join(block if isinstance(block, str) else block.get("text", "") for block in message.content).strip()


async def understand_request(state: SupportState) -> dict:
    """Ask the LLM to read the conversation and return a structured interpretation of the latest request."""
    try:
        structured_model = get_chat_model().with_structured_output(RequestUnderstanding)
        understanding = await structured_model.ainvoke([SystemMessage(content=UNDERSTANDING_SYSTEM_PROMPT), *select_conversation_messages(state["messages"])])
        if understanding is None:
            raise ValueError("LLM returned no structured understanding")
        return {
            "intent": understanding.intent.value,
            "category": understanding.category,
            "issue_summary": understanding.issue_summary,
            "entities": [entity.model_dump() for entity in understanding.entities],
            "requires_tools": understanding.requires_tools,
            "requires_knowledge": understanding.requires_knowledge,
            "is_sensitive_action": understanding.is_sensitive_action,
            "missing_information": understanding.missing_information,
            "clarifying_question": understanding.clarifying_question,
            "confidence": understanding.confidence,
        }
    except Exception as error:
        logger.exception("Request understanding failed for conversation %s", state.get("conversation_id"))
        return {"intent": Intent.UNKNOWN.value, "confidence": 0.0, "missing_information": [], "clarifying_question": None, "errors": [{"node": "understand_request", "error": str(error)}]}


def classify_request(state: SupportState) -> dict:
    """Apply fixed rules on top of the LLM output: low-confidence or unknown requests become 'unknown' with nothing to clarify."""
    is_low_confidence = state.get("confidence", 0.0) < settings.classification_confidence_threshold
    if is_low_confidence or state.get("intent") == Intent.UNKNOWN.value:
        return {"intent": Intent.UNKNOWN.value, "missing_information": [], "clarifying_question": None}
    return {}


def route_after_classification(state: SupportState) -> Literal["ask_user", "run_support_agent", "generate_response", "handle_unknown_request"]:
    """Pick the next node: unknown gets a fallback, missing details get a question, tool-backed intents go to the agent, the rest get a reply."""
    if state.get("intent") == Intent.UNKNOWN.value:
        return "handle_unknown_request"
    has_attempts_left = state.get("clarification_count", 0) < settings.max_clarification_attempts
    if state.get("missing_information") and has_attempts_left:
        return "ask_user"
    if state.get("intent") in TOOLS_BY_INTENT:
        return "run_support_agent"
    return "generate_response"


def ask_user(state: SupportState) -> dict:
    """Pause the graph with a clarifying question; the next /chat message resumes it with the user's answer."""
    missing_information = state.get("missing_information", [])
    question = state.get("clarifying_question") or f"Could you share these details: {', '.join(missing_information)}?"
    answer = interrupt({"question": question, "missing_information": missing_information})
    return {"messages": [AIMessage(content=question), HumanMessage(content=str(answer))], "clarification_count": state.get("clarification_count", 0) + 1}


async def run_support_agent(state: SupportState) -> dict:
    """Let the LLM investigate with the MCP tools allowed for this intent: each pass either asks for tool calls or writes the final answer."""
    try:
        tool_iterations = state.get("tool_iterations", 0)
        if tool_iterations >= settings.max_tool_iterations:
            logger.warning("Tool iteration limit reached for conversation %s", state.get("conversation_id"))
            return {"final_response": TOOL_LIMIT_MESSAGE, "messages": [AIMessage(content=TOOL_LIMIT_MESSAGE)]}

        tool_specs = build_llm_tool_specs(TOOLS_BY_INTENT[state["intent"]])
        if not tool_specs:
            logger.error("No MCP tools available for intent %s", state["intent"])
            return {"final_response": SYSTEMS_UNAVAILABLE_MESSAGE, "messages": [AIMessage(content=SYSTEMS_UNAVAILABLE_MESSAGE)]}

        print()
        print()
        print(tool_specs,"tool specs listing....")
        print()
        print()

        system_prompt = AGENT_SYSTEM_PROMPT.format(intent=state["intent"], issue_summary=state.get("issue_summary") or state["request"])
        reply = await get_chat_model().bind_tools(tool_specs).ainvoke([SystemMessage(content=system_prompt), *state["messages"]])
        logger.debug("Agent reply for conversation %s: tool_calls=%s", state.get("conversation_id"), [tool_call["name"] for tool_call in reply.tool_calls])

        if reply.tool_calls:
            return {"messages": [reply], "tool_iterations": tool_iterations + 1}
        reply_text = read_message_text(reply)
        if not reply_text:
            raise ValueError("Agent returned neither tool calls nor an answer")
        return {"final_response": reply_text, "messages": [reply]}
    except Exception as error:
        logger.exception("Support agent failed for conversation %s", state.get("conversation_id"))
        return {"final_response": AGENT_FAILURE_MESSAGE, "messages": [AIMessage(content=AGENT_FAILURE_MESSAGE)], "errors": [{"node": "run_support_agent", "error": str(error)}]}


async def execute_tools(state: SupportState) -> dict:
    """Run every tool call from the agent's last reply on the MCP servers in parallel, with the user's identity supplied by the backend."""
    trusted_arguments = {"employee_code": state["user_id"], "conversation_id": state["conversation_id"]}
    allowed_tool_names = TOOLS_BY_INTENT.get(state["intent"], [])
    tool_calls = state["messages"][-1].tool_calls
    tool_messages = await asyncio.gather(*(call_mcp_tool(tool_call, trusted_arguments, allowed_tool_names) for tool_call in tool_calls))
    return {"messages": list(tool_messages)}


async def generate_response(state: SupportState) -> dict:
    """Reply with a short acknowledgement of the request and the next step the agent will take."""
    next_step = "I'll look into this for you."
    try:
        intent = Intent(state["intent"])
        next_step = INTENT_NEXT_STEPS[intent]
        missing_information = ", ".join(state.get("missing_information", [])) or "nothing"
        system_prompt = RESPONSE_SYSTEM_PROMPT.format(intent=intent.value, issue_summary=state.get("issue_summary") or state["request"], next_step=next_step, missing_information=missing_information)
        reply = await get_chat_model().ainvoke([SystemMessage(content=system_prompt), *select_conversation_messages(state["messages"])])
        reply_text = read_message_text(reply)
        if not reply_text:
            raise ValueError("LLM returned an empty response")
        return {"final_response": reply_text, "messages": [AIMessage(content=reply_text)]}
    except Exception as error:
        logger.exception("Response generation failed for conversation %s", state.get("conversation_id"))
        return {"final_response": next_step, "messages": [AIMessage(content=next_step)], "errors": [{"node": "generate_response", "error": str(error)}]}


def handle_unknown_request(state: SupportState) -> dict:
    """Tell the user the request was not understood and list what the agent can help with."""
    return {"final_response": UNKNOWN_REQUEST_MESSAGE, "messages": [AIMessage(content=UNKNOWN_REQUEST_MESSAGE)]}


def build_graph(check_pointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Assemble the Phase 3 support workflow (understanding, clarification, MCP-backed agent loop) and compile it with a checkpointer."""
    workflow = StateGraph(SupportState)
    workflow.add_node("understand_request", understand_request)
    workflow.add_node("classify_request", classify_request)
    workflow.add_node("ask_user", ask_user)
    workflow.add_node("run_support_agent", run_support_agent)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("handle_unknown_request", handle_unknown_request)

    workflow.add_edge(START, "understand_request")
    workflow.add_edge("understand_request", "classify_request")
    workflow.add_conditional_edges("classify_request", route_after_classification, ["ask_user", "run_support_agent", "generate_response", "handle_unknown_request"])
    workflow.add_edge("ask_user", "understand_request")
    workflow.add_conditional_edges("run_support_agent", tools_condition, {"tools": "execute_tools", END: END})
    workflow.add_edge("execute_tools", "run_support_agent")
    workflow.add_edge("generate_response", END)
    workflow.add_edge("handle_unknown_request", END)

    return workflow.compile(checkpointer=check_pointer or InMemorySaver())
