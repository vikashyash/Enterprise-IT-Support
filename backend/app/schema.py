from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Intent(str, Enum):
    """The IT support request types the agent understands in Phase 1."""

    KNOWLEDGE = "knowledge"
    TROUBLESHOOTING = "troubleshooting"
    ACCESS_REQUEST = "access_request"
    SOFTWARE_REQUEST = "software_request"
    SECURITY_ISSUE = "security_issue"
    TICKET_REQUEST = "ticket_request"
    UNKNOWN = "unknown"


class Entity(BaseModel):
    """A concrete thing mentioned by the user, such as an application, device or resource."""

    type: str = Field(description="Entity kind, for example application, device, service, resource")
    value: str = Field(description="Entity value exactly as the user referred to it")


class RequestUnderstanding(BaseModel):
    """Structured interpretation of the user's request produced by the LLM."""

    intent: Intent
    category: str | None = Field(default=None, description="IT area such as network, email, hardware, software, access, security")
    issue_summary: str = Field(description="One short sentence describing the user's problem or goal")
    entities: list[Entity] = Field(default_factory=list)
    requires_tools: bool = Field(description="True if live IT systems must be checked or changed")
    requires_knowledge: bool = Field(description="True if internal IT documentation or policy is needed")
    is_sensitive_action: bool = Field(description="True for access, installation, password or security changes")
    missing_information: list[str] = Field(default_factory=list, description="Critical details the user must still provide")
    clarifying_question: str | None = Field(default=None, description="One short question asking for the missing details")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the chosen intent")


class ChatRequest(BaseModel):
    """Incoming chat message. user_id is temporary until JWT authentication arrives in Phase 10."""

    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: str | None = Field(default=None, min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    """Reply returned to the client for one chat turn."""

    conversation_id: str
    message: str
    status: Literal["completed", "waiting_user"]
    intent: Intent | None = None
    actions: list[dict] = Field(default_factory=list)
    tickets: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)