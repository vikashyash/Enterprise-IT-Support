import logging
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from app.config import settings
from app.graph import UNKNOWN_REQUEST_MESSAGE, build_graph
from app.schema import ChatRequest, ChatResponse

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

support_graph = build_graph()
app = FastAPI(title=settings.app_name)


async def find_pending_question(thread_config: dict) -> str | None:
    """Return the clarifying question a conversation is paused on, or None if it is not waiting for the user."""
    try:
        snapshot = await support_graph.aget_state(thread_config)
        for task in snapshot.tasks:
            for pending_interrupt in task.interrupts:
                return pending_interrupt.value.get("question")
        return None
    except Exception:
        logger.exception("Could not read graph state for thread %s", thread_config["configurable"]["thread_id"])
        raise


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Report that the API process is up."""
    try:
        return {"status": "ok", "environment": settings.app_env}
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest) -> ChatResponse:
    """Run one user turn: resume the conversation if it is waiting on a question, otherwise start a new turn."""
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
                "final_response": None,
            }

        result = await support_graph.ainvoke(graph_input, config=thread_config)

        pending_question = await find_pending_question(thread_config)
        if pending_question:
            return ChatResponse(conversation_id=conversation_id, message=pending_question, status="waiting_user", intent=result.get("intent"))
        return ChatResponse(conversation_id=conversation_id, message=result.get("final_response") or UNKNOWN_REQUEST_MESSAGE, status="completed", intent=result.get("intent"))
    except Exception:
        logger.exception("Chat turn failed for conversation %s", chat_request.conversation_id)
        raise HTTPException(status_code=500, detail="The support agent could not process this request. Please try again.")

if __name__=="__main__":
    uvicorn.run(
        host="0.0.0.0",
        app="app.main:app",
        port=8080
    )