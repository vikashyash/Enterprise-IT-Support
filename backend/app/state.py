import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupportState(TypedDict, total=False):
    """Everything the support graph needs to carry between nodes within a conversation."""

    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    conversation_id: str
    request: str

    intent: str | None
    category: str | None
    issue_summary: str
    entities: list[dict]
    requires_tools: bool
    requires_knowledge: bool
    is_sensitive_action: bool
    confidence: float

    missing_information: list[str]
    clarifying_question: str | None
    clarification_count: int

    tool_iterations: int
    retrieved_documents: list[dict]

    final_response: str | None
    errors: Annotated[list[dict], operator.add]
