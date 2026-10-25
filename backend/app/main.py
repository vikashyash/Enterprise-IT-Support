import json
import logging
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command

from app.config import settings
from app.graph import UNKNOWN_REQUEST_MESSAGE, build_graph
from app.mcp_client import MCP_SERVERS, available_tools, connected_servers, load_mcp_tools
from app.schema import ChatRequest, ChatResponse, TicketReference, ToolAction

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

support_graph = build_graph()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Discover the MCP tools before the API starts taking requests."""
    await load_mcp_tools()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


async def find_pending_question(thread_config: dict) -> str | None:
    """Return the clarifying question a conversation is paused on, or None if it is not waiting for the user."""
    snapshot = await support_graph.aget_state(thread_config)
    for task in snapshot.tasks:
        for pending_interrupt in task.interrupts:
            return pending_interrupt.value.get("question")
    return None


@app.get("/health")
async def health_check() -> dict:
    """Report whether the API is up and which MCP servers and tools it can currently use."""
    status = "ok" if len(connected_servers) == len(MCP_SERVERS) else "degraded"
    return {"status": status, "environment": settings.app_env, "mcp_servers": connected_servers, "mcp_tools": len(available_tools)}


@app.post("/mcp/reload")
async def reload_mcp_tools() -> dict:
    """Rediscover MCP tools, for example after starting a server that was down when the API booted."""
    await load_mcp_tools()
    return {"mcp_servers": connected_servers, "mcp_tools": len(available_tools)}


@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest) -> ChatResponse:
    """Run one user turn: resume a paused conversation or start a new turn, then report the reply, tools used and tickets."""
    try:
        conversation_id = chat_request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        thread_config = {"configurable": {"thread_id": conversation_id}}

        if await find_pending_question(thread_config):
            graph_input = Command(resume=chat_request.message)
        else:
            graph_input = {
                "messages": [HumanMessage(content=chat_request.message)],
                "user_id": chat_request.user_id,
                "conversation_id": conversation_id,
                "request": chat_request.message,
                "intent": None,
                "missing_information": [],
                "clarifying_question": None,
                "clarification_count": 0,
                "tool_iterations": 0,
                "final_response": None,
            }

        result = await support_graph.ainvoke(graph_input, config=thread_config)

        pending_question = await find_pending_question(thread_config)
        if pending_question:
            return ChatResponse(conversation_id=conversation_id, message=pending_question, status="waiting_user", intent=result.get("intent"))

        actions: list[ToolAction] = []
        tickets: list[TicketReference] = []
        for message in reversed(result.get("messages", [])):
            if isinstance(message, HumanMessage):
                break
            if not isinstance(message, ToolMessage):
                continue
            try:
                tool_output = json.loads(message.content) if isinstance(message.content, str) else {}
            except json.JSONDecodeError:
                tool_output = {}
            succeeded = message.status != "error" and tool_output.get("ok") is True
            actions.insert(0, ToolAction(tool=message.name or "unknown", status="succeeded" if succeeded else "failed"))
            if message.name == "create_ticket" and succeeded:
                tickets.insert(0, TicketReference(**tool_output["ticket"], created=tool_output["created"]))

        logger.info("Conversation %s completed with intent=%s tools=%s tickets=%s", conversation_id, result.get("intent"), [action.tool for action in actions], [ticket.ticket_number for ticket in tickets])
        return ChatResponse(conversation_id=conversation_id, message=result.get("final_response") or UNKNOWN_REQUEST_MESSAGE, status="completed", intent=result.get("intent"), actions=actions, tickets=tickets)
    except Exception:
        logger.exception("Chat turn failed for conversation %s", chat_request.conversation_id)
        raise HTTPException(status_code=500, detail="The support agent could not process this request. Please try again.")


if __name__ == "__main__":
    uvicorn.run(app="app.main:app", host="0.0.0.0", port=8080)
