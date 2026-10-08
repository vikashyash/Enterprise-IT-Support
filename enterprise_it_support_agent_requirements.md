# Enterprise IT Support Agent

## Production-Grade Agentic AI Learning Project --- Requirements & Development Specification

**Document version:** 1.0\
**Status:** Development specification\
**Primary goal:** Build a realistic enterprise IT support platform that
deeply exercises LangGraph, MCP, agentic workflows, RAG, tool calling,
state persistence, human-in-the-loop, error recovery, observability,
evaluation, and production deployment.

------------------------------------------------------------------------

# 1. Project Overview

Build an **Enterprise IT Support Agent** for an organization with
employees, laptops/desktops, applications, IT services, access-control
systems, tickets, and internal IT documentation.

The application should allow employees to interact with an AI support
agent using natural language.

Examples:

-   "My laptop is connected to Wi-Fi but VPN is not working."
-   "Outlook stopped syncing."
-   "My laptop has become very slow."
-   "I forgot my password."
-   "I need access to the Finance shared drive."
-   "Can you install Docker on my laptop?"
-   "Why can't I access GitHub?"
-   "I think someone logged into my account."
-   "Is the company VPN currently down?"
-   "Create an IT ticket for my printer issue."

The system must not behave like a simple chatbot.

It should:

1.  Understand the user's request.
2.  Determine what information is required.
3.  Decide whether knowledge retrieval, tool execution, or both are
    required.
4.  Select appropriate tools.
5.  Execute multi-step workflows.
6.  Inspect tool results.
7.  Decide the next action dynamically.
8.  Recover from tool/API failures.
9.  Maintain state throughout the workflow.
10. Ask the user for missing information when required.
11. Pause for human approval for sensitive actions.
12. Resume long-running workflows after approval.
13. Produce a grounded final response.
14. Record enough information to evaluate and debug the agent.

------------------------------------------------------------------------

# 2. Learning Objectives

The project is intentionally designed as a practical learning project.

The implementation should progressively teach the following.

## 2.1 LangGraph

The application must demonstrate:

-   Graphs
-   State
-   Nodes
-   Conditional routing
-   Loops
-   Checkpoints
-   Persistent state
-   Interrupts
-   Resume
-   Subgraphs
-   Error recovery
-   Human-in-the-loop
-   Streaming
-   Long-running workflows

## 2.2 Agents

The system should demonstrate:

-   Tool selection
-   Dynamic planning
-   Re-planning
-   Reasoning over tool results
-   Multi-step investigation
-   Agent handoff
-   Controlled autonomy
-   Agent boundaries
-   Deterministic vs agentic decisions

## 2.3 MCP

The application must expose external capabilities through MCP servers.

The agent should not directly contain all integration logic.

MCP should be used as the capability boundary between the agent and
external systems.

## 2.4 RAG

The system must retrieve information from internal IT documentation such
as:

-   Troubleshooting guides
-   Security policies
-   Password policies
-   Software installation policies
-   VPN documentation
-   Email documentation
-   Hardware troubleshooting
-   Access-control policies
-   Onboarding documentation

## 2.5 Production AI Engineering

The application should eventually demonstrate:

-   Authentication
-   Authorization
-   Tool permissions
-   Audit logs
-   Observability
-   Evaluation
-   Retry handling
-   Idempotency
-   Rate limiting
-   Cost tracking
-   Latency tracking
-   Secure secrets handling
-   Docker deployment
-   API separation
-   Persistent storage

------------------------------------------------------------------------

# 3. Core Architectural Principle

The application must NOT be designed as:

``` text
User -> LLM -> Tool -> Answer
```

Instead, it should be designed as a stateful workflow:

``` text
User
  |
  v
Request Understanding
  |
  v
Planning
  |
  v
Capability Selection
  |
  +-------------------+
  |                   |
  v                   v
Knowledge           External
Retrieval           Systems
  |                   |
  +---------+---------+
            |
            v
       Result Analysis
            |
            v
       Re-planning
            |
       +----+----+
       |         |
       v         v
   Resolved   More Work
       |         |
       |         +------> Tool / RAG / Agent
       |
       v
   Final Response
```

The agent should be able to dynamically determine the next step.

------------------------------------------------------------------------

# 4. High-Level System Architecture

Target architecture:

``` text
                         +----------------------+
                         |       React UI       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       FastAPI        |
                         |     API Gateway      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |     LangGraph        |
                         |   Agent Runtime      |
                         +----------+-----------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
              v                     v                     v
      +---------------+     +---------------+     +---------------+
      |   IT Support  |     |   Knowledge   |     |    Security   |
      |     Agent     |     |     / RAG     |     |     Agent     |
      +-------+-------+     +-------+-------+     +-------+-------+
              |                     |                     |
              +---------------------+---------------------+
                                    |
                                    v
                         +----------------------+
                         |      MCP Layer       |
                         +----------+-----------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
   +-------------+           +-------------+           +-------------+
   | ITSM MCP    |           | Device MCP  |           | IAM MCP     |
   +-------------+           +-------------+           +-------------+
          |                         |                         |
          v                         v                         v
      Ticket DB                Device DB                 Access DB

                         +----------------------+
                         | Infrastructure MCP   |
                         +----------+-----------+
                                    |
                                    v
                             Service Status

                         +----------------------+
                         |      RAG Layer        |
                         +----------+-----------+
                                    |
                                    v
                           Vector Database
                                    |
                                    v
                         Enterprise IT Documents

                         +----------------------+
                         | PostgreSQL / Redis    |
                         | State / Audit / Data  |
                         +----------------------+
```

------------------------------------------------------------------------

# 5. Recommended Technology Stack

Use the following stack unless there is a strong technical reason to
change it.

## Backend

-   Python 3.12+
-   FastAPI
-   LangGraph
-   LangChain where useful
-   MCP Python SDK
-   Pydantic
-   SQLAlchemy
-   PostgreSQL
-   Redis

## AI

The architecture must keep the LLM provider replaceable.

Initial implementation may use:

-   AWS Bedrock

The application should avoid tightly coupling business logic to one
model provider.

## RAG

Initial implementation:

-   PostgreSQL + pgvector, or a dedicated vector database if required.

Embeddings must be configurable.

## Frontend

-   React
-   TypeScript
-   Simple enterprise support-chat interface

The frontend is not the main learning target. Keep it clean and minimal.

## Infrastructure

-   Docker
-   Docker Compose for local development

------------------------------------------------------------------------

# 6. Domain Model

The system should simulate a realistic enterprise IT environment.

Core entities:

``` text
Company
Department
Employee
Device
OperatingSystem
Software
SoftwareLicense
ITService
Ticket
TicketComment
Incident
AccessRequest
Permission
KnowledgeDocument
AuditLog
AgentExecution
ApprovalRequest
```

------------------------------------------------------------------------

# 7. Database Requirements

Use PostgreSQL.

Create realistic seed data.

## 7.1 employees

Fields:

``` text
id
employee_code
name
email
department_id
manager_id
job_title
status
created_at
updated_at
```

## 7.2 departments

``` text
id
name
description
```

Example:

``` text
Engineering
Finance
HR
Sales
Operations
Security
IT
Management
```

## 7.3 devices

``` text
id
asset_tag
employee_id
hostname
device_type
manufacturer
model
operating_system
os_version
cpu
ram_gb
storage_total_gb
storage_free_gb
ip_address
mac_address
last_seen_at
status
```

## 7.4 installed_software

``` text
id
device_id
software_id
version
installed_at
status
```

## 7.5 software

``` text
id
name
vendor
latest_version
license_required
approval_required
installation_allowed
category
```

## 7.6 services

``` text
id
name
service_type
status
health
last_checked_at
```

Examples:

``` text
VPN
Microsoft 365
Outlook
Teams
GitHub Enterprise
DNS
SSO
Active Directory
File Storage
```

## 7.7 tickets

``` text
id
ticket_number
employee_id
title
description
category
subcategory
priority
status
assigned_team
assigned_to
created_at
updated_at
resolved_at
```

## 7.8 ticket_comments

``` text
id
ticket_id
author_type
author_id
comment
created_at
```

## 7.9 access_requests

``` text
id
employee_id
resource
requested_role
reason
status
requested_at
approved_by
approved_at
completed_at
```

## 7.10 permissions

``` text
id
employee_id
resource
role
status
granted_at
revoked_at
```

## 7.11 incidents

``` text
id
incident_number
title
description
affected_service
severity
status
started_at
resolved_at
```

## 7.12 audit_logs

``` text
id
user_id
agent_run_id
action
resource_type
resource_id
details
result
created_at
```

------------------------------------------------------------------------

# 8. MCP Architecture

Create separate MCP servers based on capability boundaries.

Do not create one enormous MCP server containing every tool.

Initial servers:

``` text
mcp-itsm
mcp-device
mcp-infrastructure
mcp-iam
```

A knowledge/RAG MCP server may be added later.

------------------------------------------------------------------------

# 9. ITSM MCP Server

Responsibilities:

-   Ticket management
-   Incident lookup
-   Ticket search
-   Ticket comments

Tools:

``` text
create_ticket
get_ticket
search_tickets
update_ticket
add_ticket_comment
close_ticket
search_incidents
get_incident
```

## create_ticket

Input:

``` text
employee_id
title
description
category
priority
```

Output:

``` json
{
  "ticket_id": 123,
  "ticket_number": "INC-100123",
  "status": "OPEN"
}
```

The tool must validate inputs.

The tool must be idempotent where appropriate.

------------------------------------------------------------------------

# 10. Device MCP Server

Responsibilities:

-   Employee device lookup
-   Device health
-   Device configuration
-   Installed software

Tools:

``` text
get_employee
get_employee_devices
get_device
get_device_status
get_device_network_info
get_installed_software
get_device_storage
get_device_performance
```

Example:

``` text
get_device_performance(device_id)
```

Output:

``` json
{
  "cpu_percent": 87.3,
  "memory_percent": 91.2,
  "disk_percent": 96.8,
  "top_processes": [
    {
      "name": "example.exe",
      "cpu_percent": 42.1
    }
  ]
}
```

------------------------------------------------------------------------

# 11. Infrastructure MCP Server

Responsibilities:

-   Enterprise service health
-   Network status
-   VPN status
-   DNS status
-   SSO status
-   Email service status

Tools:

``` text
check_service_health
check_vpn_status
check_network_status
check_dns_status
check_sso_status
check_email_service
search_active_incidents
```

The implementation may initially use mock data.

However, the interface must resemble a real enterprise integration.

------------------------------------------------------------------------

# 12. IAM MCP Server

Responsibilities:

-   Access lookup
-   Software license checks
-   Access requests
-   Software installation requests

Tools:

``` text
get_user_permissions
check_user_access
check_software_license
request_access
request_software_installation
revoke_access
```

Sensitive operations must have authorization checks.

------------------------------------------------------------------------

# 13. Tool Safety Rules

Never allow the LLM to directly perform sensitive operations without
deterministic validation.

Sensitive operations include:

``` text
password reset
access grant
access revoke
software installation
account disablement
device wipe
security changes
production configuration changes
```

The architecture should be:

``` text
LLM decision
    |
    v
Policy validation
    |
    v
Authorization check
    |
    v
Human approval if required
    |
    v
MCP tool
```

Not:

``` text
LLM -> dangerous tool
```

------------------------------------------------------------------------

# 14. LangGraph State

Create a strongly typed graph state.

Suggested state:

``` python
class SupportState:
    user_id: str
    conversation_id: str
    request: str

    intent: str | None
    category: str | None

    entities: dict
    missing_information: list[str]

    plan: list[dict]
    current_step: str | None

    tool_calls: list[dict]
    tool_results: list[dict]

    retrieved_documents: list[dict]

    hypotheses: list[dict]
    selected_hypothesis: str | None

    resolution_status: str

    approval_required: bool
    approval_request_id: str | None
    approval_status: str | None

    retry_count: int

    final_response: str | None

    errors: list[dict]
```

Keep state focused on information required to continue the workflow.

Do not store arbitrary LLM output in state without a reason.

------------------------------------------------------------------------

# 15. Main LangGraph

Initial graph:

``` text
START
  |
  v
understand_request
  |
  v
classify_request
  |
  v
check_missing_information
  |
  +---- missing ----> ask_user
  |                      |
  |                      v
  |                  resume_graph
  |
  +---- complete
           |
           v
       create_plan
           |
           v
       execute_plan
           |
           v
      analyze_result
           |
      +----+----+
      |         |
      v         v
  resolved   unresolved
      |         |
      v         v
 final_answer  replan
                |
                +------> execute_plan
```

------------------------------------------------------------------------

# 16. Request Understanding

The first agent should determine:

-   What is the user trying to accomplish?
-   Is the request informational?
-   Is troubleshooting required?
-   Is an action requested?
-   Is the action sensitive?
-   What entities are present?
-   What information is missing?

Example:

User:

> "My laptop is slow."

Structured interpretation:

``` json
{
  "intent": "troubleshoot",
  "category": "hardware",
  "issue": "slow_device",
  "requires_tools": true,
  "requires_knowledge": true
}
```

Do not immediately execute a tool.

------------------------------------------------------------------------

# 17. Dynamic Planning

The agent should generate a plan based on the request.

Example:

``` text
User:
"My laptop is very slow."

Plan:
1. Identify user's active device.
2. Check device health.
3. Check storage.
4. Check CPU and memory.
5. Search troubleshooting documentation if required.
6. Determine likely cause.
7. Recommend or execute permitted remediation.
8. Create ticket if unresolved.
```

The plan must be treated as mutable.

The agent should be able to change the plan after receiving tool
results.

------------------------------------------------------------------------

# 18. Agentic Troubleshooting

This is one of the most important parts of the project.

The troubleshooting agent should not always follow a fixed sequence.

Example:

``` text
User:
"VPN isn't working."
```

Possible reasoning flow:

``` text
Get device
    |
Check network
    |
Network OK
    |
Check VPN service
    |
Service OK
    |
Check VPN client
    |
Client outdated
    |
Check software policy
    |
Update allowed
    |
Request/update
```

Another scenario:

``` text
Get device
    |
Check network
    |
Network unavailable
    |
No need to check VPN
    |
Provide network remediation
```

The graph should therefore support conditional paths.

------------------------------------------------------------------------

# 19. RAG Requirements

Create a document ingestion pipeline.

Input:

``` text
PDF
DOCX
Markdown
TXT
```

Processing:

``` text
Load document
    |
Extract text
    |
Clean
    |
Chunk
    |
Generate embeddings
    |
Store vector
    |
Store metadata
```

Metadata should include:

``` text
document_id
title
category
department
version
effective_date
source
access_level
```

------------------------------------------------------------------------

# 20. RAG Retrieval

The agent should use RAG when company-specific knowledge is required.

Examples:

> "What is the company policy for installing software?"

> "How do I configure the corporate VPN on Windows?"

> "Can employees install Docker?"

The answer should be grounded in retrieved documents.

Do not let the model invent company policies.

------------------------------------------------------------------------

# 21. RAG + Tools

The interesting cases require both.

Example:

> "Can I install Docker on my laptop?"

Workflow:

``` text
RAG
 |
Check software policy
 |
MCP
 |
Check software catalog
 |
MCP
 |
Check user permissions
 |
MCP
 |
Check license
 |
Agent
 |
Determine whether approval is required
```

This should be a core demonstration of the project.

------------------------------------------------------------------------

# 22. Human-in-the-Loop

Use LangGraph interrupts.

Example:

``` text
User:
"Install Docker for me."
```

Workflow:

``` text
Understand request
       |
Check policy
       |
Check authorization
       |
Installation requires approval
       |
       v
INTERRUPT
       |
       v
Approval UI
       |
Approve / Reject
       |
       v
Resume graph
       |
       v
Execute MCP tool
```

The graph must survive application restarts.

------------------------------------------------------------------------

# 23. Long-Running Workflow

Implement at least one workflow that can remain pending.

Example:

``` text
Request access to Finance shared drive
```

Workflow:

``` text
Validate request
    |
Create access request
    |
Wait for approval
    |
Manager approves
    |
Resume graph
    |
Grant access
    |
Verify
    |
Notify user
```

This is required to demonstrate durable execution.

------------------------------------------------------------------------

# 24. Multi-Agent Architecture

Do not begin with multiple agents.

First make the single-agent workflow work.

Later introduce:

``` text
Supervisor
    |
    +---- IT Support Agent
    |
    +---- Security Agent
    |
    +---- Access Agent
```

## Supervisor

Responsibilities:

-   Understand overall request
-   Select specialist
-   Maintain global state
-   Combine specialist results

## IT Support Agent

Handles:

-   Device issues
-   VPN
-   Email
-   Network
-   Application troubleshooting

## Security Agent

Handles:

-   Suspicious login
-   MFA
-   Security incidents
-   Account compromise

## Access Agent

Handles:

-   Application access
-   Shared drive access
-   Software requests
-   Permission requests

------------------------------------------------------------------------

# 25. Agent Boundaries

Agents should not directly bypass:

-   Authentication
-   Authorization
-   Policy validation
-   Security controls
-   Human approval

The agent is responsible for reasoning.

Deterministic services are responsible for enforcing rules.

------------------------------------------------------------------------

# 26. Example Workflow: Outlook Problem

User:

> "Outlook hasn't synced my emails since this morning."

Expected workflow:

``` text
Understand request
      |
Identify user
      |
Identify device
      |
Check email service health
      |
Service healthy?
      |
      +--- NO ---> Existing incident -> inform user
      |
      +--- YES
             |
             v
       Check device
             |
             v
       Check Outlook status
             |
             v
       Search troubleshooting KB
             |
             v
       Recommend next action
             |
             v
       Verify
             |
        +----+----+
        |         |
      fixed    unresolved
        |         |
        v         v
      answer    ticket
```

------------------------------------------------------------------------

# 27. Example Workflow: Suspicious Login

User:

> "I received an MFA request that I didn't initiate."

Expected route:

``` text
Supervisor
    |
Security Agent
    |
Get user
    |
Check recent authentication events
    |
Check MFA events
    |
Check active sessions
    |
Check security policy
    |
Determine recommended action
    |
Sensitive action?
    |
Human approval if required
    |
Execute security operation
    |
Create security incident
    |
Final response
```

Security actions should be deterministic and auditable.

------------------------------------------------------------------------

# 28. Example Workflow: Access Request

User:

> "I need access to the Finance shared drive."

Workflow:

``` text
Identify employee
    |
Identify resource
    |
Check current permission
    |
Check access policy
    |
Check whether approval is required
    |
Create access request
    |
Interrupt / wait
    |
Approval
    |
Grant access
    |
Verify
    |
Notify user
```

------------------------------------------------------------------------

# 29. Clarification Handling

The agent must not guess critical information.

Example:

> "Install the application for me."

If multiple applications are available:

``` text
Which application would you like me to install?
```

For sensitive actions:

``` text
Which system should I request access to?
```

The graph should pause and resume with the user's answer.

------------------------------------------------------------------------

# 30. Conversation Memory

Use persistent conversation state.

Each conversation should have:

``` text
conversation_id
user_id
created_at
updated_at
state/checkpoint
```

The agent should remember relevant information during the conversation.

Example:

``` text
User:
VPN doesn't work.

Agent:
Which device are you using?

User:
My company laptop.

User:
I already restarted it.
```

The agent should know that restarting was already attempted.

It should not repeatedly recommend the same action unless there is a
reason.

------------------------------------------------------------------------

# 31. Error Recovery

Every tool call should be treated as potentially failing.

Possible failures:

``` text
timeout
authentication failure
authorization failure
invalid input
service unavailable
rate limit
database error
duplicate request
MCP server unavailable
```

Implement:

``` text
Tool call
   |
Error
   |
Classify error
   |
   +---- retryable ------> retry
   |
   +---- invalid input --> repair
   |
   +---- unauthorized ---> ask user / stop
   |
   +---- unavailable ----> fallback
   |
   +---- fatal ----------> ticket / graceful failure
```

Do not blindly retry every error.

------------------------------------------------------------------------

# 32. Retry Strategy

Retries must be bounded.

Example:

``` text
max_retries = 2 or 3
```

Use exponential backoff for transient failures.

Track:

``` text
tool_name
attempt
error
timestamp
```

The graph state should contain retry information.

------------------------------------------------------------------------

# 33. Idempotency

Actions that can create duplicate resources must be idempotent where
possible.

Example:

If the agent retries:

``` text
create_access_request()
```

it must not accidentally create two identical requests.

Use an idempotency key such as:

``` text
conversation_id + action_type + resource
```

where appropriate.

------------------------------------------------------------------------

# 34. Authentication

Users should authenticate to the FastAPI application.

For the initial project, a simple JWT-based authentication system is
sufficient.

Every request should contain:

``` text
user_id
conversation_id
authentication context
```

The agent must never trust a user-provided `employee_id` without
authorization validation.

------------------------------------------------------------------------

# 35. Authorization

Implement role-based permissions.

Example roles:

``` text
EMPLOYEE
IT_AGENT
IT_ADMIN
SECURITY_ADMIN
MANAGER
```

Example:

``` text
EMPLOYEE
    |
    +-- create ticket
    +-- view own ticket
    +-- request access

IT_AGENT
    |
    +-- update tickets
    +-- troubleshoot devices

IT_ADMIN
    |
    +-- software installation
    +-- device remediation

SECURITY_ADMIN
    |
    +-- security actions
```

Authorization must be enforced outside the LLM.

------------------------------------------------------------------------

# 36. Auditability

Every important agent action must be auditable.

Log:

``` text
user_id
conversation_id
agent_run_id
node_name
tool_name
tool_input
tool_output
action
authorization_result
approval_status
timestamp
error
```

Do not log passwords, access tokens, API keys, or other secrets.

------------------------------------------------------------------------

# 37. Observability

Implement structured logging.

Track each agent run:

``` text
run_id
conversation_id
user_id
start_time
end_time
duration
model
input_tokens
output_tokens
tool_calls
tool_failures
final_status
```

Track graph transitions:

``` text
node
previous_node
next_node
duration
status
```

This should make it possible to answer:

> "Why did the agent do this?"

without manually reading application logs.

------------------------------------------------------------------------

# 38. Agent Evaluation

Create a test dataset.

Example:

``` text
tests/evaluation/questions.json
```

Include at least 100 scenarios eventually.

Categories:

``` text
VPN
Email
Network
Hardware
Software
Access
Security
Password
Tickets
Incidents
General IT knowledge
```

For each test case define expected properties.

Example:

``` json
{
  "question": "My VPN isn't connecting",
  "expected_category": "network",
  "expected_tools": [
    "get_device",
    "check_network_status",
    "check_vpn_status"
  ],
  "requires_rag": true
}
```

Do not require an exact natural-language answer match.

Evaluate structured behavior.

------------------------------------------------------------------------

# 39. Evaluation Metrics

Track:

## Intent accuracy

Did the system identify the correct category?

## Tool selection accuracy

Did it use the appropriate capability?

## Tool argument accuracy

Were correct IDs and parameters supplied?

## RAG retrieval quality

Did the system retrieve relevant documentation?

## Workflow success rate

Did the issue reach the correct resolution?

## Hallucination rate

Did the system claim something unsupported?

## Safety violations

Did the agent attempt unauthorized actions?

Target:

``` text
0 unauthorized sensitive actions
```

## Latency

Measure:

``` text
end-to-end latency
LLM latency
tool latency
RAG latency
```

## Cost

Track token usage and estimated model cost.

------------------------------------------------------------------------

# 40. Testing Strategy

Use multiple levels.

## Unit tests

Test:

-   Policy functions
-   Authorization
-   MCP tools
-   Database functions
-   RAG retrieval
-   State transformations

## Integration tests

Test:

``` text
LangGraph -> MCP -> Database
LangGraph -> RAG
LangGraph -> approval
```

## Agent tests

Use fixed scenarios.

## Failure tests

Simulate:

``` text
MCP timeout
database failure
invalid tool input
LLM malformed output
approval rejection
duplicate request
```

------------------------------------------------------------------------

# 41. API Design

FastAPI endpoints:

``` text
POST   /auth/login
POST   /chat
GET    /conversations
GET    /conversations/{id}
GET    /tickets
GET    /tickets/{id}
POST   /approvals/{id}/approve
POST   /approvals/{id}/reject
GET    /agent-runs/{id}
GET    /health
```

Streaming endpoint may be added:

``` text
POST /chat/stream
```

Use Server-Sent Events or another suitable streaming mechanism.

------------------------------------------------------------------------

# 42. Chat API

Request:

``` json
{
  "conversation_id": "optional",
  "message": "My VPN isn't working"
}
```

Response should eventually support structured information:

``` json
{
  "conversation_id": "conv_123",
  "message": "I found that your device is online but the VPN client is outdated.",
  "status": "completed",
  "actions": [],
  "tickets": [],
  "sources": []
}
```

Do not expose raw chain-of-thought.

Return concise decision summaries, tool/action status, and relevant
evidence instead.

------------------------------------------------------------------------

# 43. Frontend Requirements

The UI should contain:

``` text
+------------------------------------------------------+
| Enterprise IT Support                                |
+------------------------------------------------------+
|                                                      |
| User: My VPN isn't working                           |
|                                                      |
| Agent: I'll check your device and VPN service.       |
|                                                      |
| Agent: Device network is healthy.                   |
|                                                      |
| Agent: VPN service is healthy.                       |
|                                                      |
| Agent: Your VPN client appears outdated.             |
|                                                      |
| [Conversation input...............................]  |
|                                             [Send]   |
+------------------------------------------------------+
```

For approval:

``` text
+----------------------------------------------+
| Approval Required                            |
+----------------------------------------------+
| Action: Install Docker                       |
| Device: LAPTOP-123                           |
| Reason: Requested by employee                |
|                                              |
|             [Reject] [Approve]               |
+----------------------------------------------+
```

The UI should show workflow status without exposing internal reasoning.

------------------------------------------------------------------------

# 44. Project Directory Structure

Start with a clean structure.

Suggested:

``` text
enterprise-it-support-agent/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── graph/
│   │   ├── mcp/
│   │   ├── rag/
│   │   ├── services/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── policies/
│   │   ├── schemas/
│   │   ├── config/
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── mcp-servers/
│   ├── itsm/
│   ├── device/
│   ├── infrastructure/
│   └── iam/
│
├── frontend/
│   └── ...
│
├── knowledge/
│   ├── vpn/
│   ├── email/
│   ├── security/
│   ├── software/
│   ├── hardware/
│   └── access/
│
├── scripts/
│   ├── seed_database.py
│   ├── ingest_documents.py
│   └── generate_test_data.py
│
├── evaluation/
│   ├── datasets/
│   ├── runners/
│   └── reports/
│
├── docker/
├── docker-compose.yml
├── .env.example
├── README.md
└── ARCHITECTURE.md
```

Avoid creating unnecessary abstractions.

Prefer straightforward modules over generic framework-like utility
layers.

------------------------------------------------------------------------

# 45. Development Phases

The project must be developed incrementally.

Do not implement everything at once.

## Phase 1 --- Basic LangGraph

Build:

``` text
User
  |
Request understanding
  |
Classification
  |
Response
```

Requirements:

-   LangGraph state
-   Nodes
-   Conditional routing

No MCP yet.

------------------------------------------------------------------------

## Phase 2 --- Tool Calling

Add mock tools directly.

Implement:

``` text
get_employee
get_device
check_vpn_status
create_ticket
```

Learn:

-   Tool calling
-   Tool results
-   Loops
-   Dynamic routing

------------------------------------------------------------------------

## Phase 3 --- MCP

Move capabilities into MCP servers.

Implement:

``` text
mcp-itsm
mcp-device
mcp-infrastructure
mcp-iam
```

The LangGraph application becomes an MCP client.

------------------------------------------------------------------------

## Phase 4 --- RAG

Implement:

``` text
document ingestion
embedding
vector search
retrieval
metadata filtering
```

Connect RAG to the agent.

------------------------------------------------------------------------

## Phase 5 --- Agentic Troubleshooting

Implement dynamic plans.

The agent should:

``` text
observe
plan
act
observe
re-plan
act
```

Introduce loops.

------------------------------------------------------------------------

## Phase 6 --- Human Approval

Implement LangGraph interrupts.

Start with:

``` text
software installation
access request
```

------------------------------------------------------------------------

## Phase 7 --- Persistent State

Add:

``` text
PostgreSQL
Redis if required
LangGraph checkpoint persistence
```

Support conversations that survive process restarts.

------------------------------------------------------------------------

## Phase 8 --- Multi-Agent

Introduce:

``` text
Supervisor
IT Agent
Security Agent
Access Agent
```

Only after the single-agent architecture is stable.

------------------------------------------------------------------------

## Phase 9 --- Observability & Evaluation

Add:

``` text
agent run logs
tool logs
latency
tokens
cost
evaluation datasets
evaluation reports
```

------------------------------------------------------------------------

## Phase 10 --- Production Hardening

Implement:

``` text
authentication
authorization
audit logging
rate limiting
secret management
Docker
health checks
structured logging
error handling
security controls
```

------------------------------------------------------------------------

# 46. Required Demo Scenarios

The completed system must demonstrate at least these workflows.

## Scenario 1 --- Simple knowledge question

``` text
"What is the company VPN setup process?"
```

Expected:

``` text
RAG -> answer with sources
```

------------------------------------------------------------------------

## Scenario 2 --- Device troubleshooting

``` text
"My laptop is very slow."
```

Expected:

``` text
Agent
 -> device MCP
 -> performance tools
 -> reasoning
 -> troubleshooting KB
 -> recommendation
```

------------------------------------------------------------------------

## Scenario 3 --- VPN troubleshooting

``` text
"My VPN isn't working."
```

Expected:

``` text
Agent
 -> device
 -> network
 -> VPN
 -> KB
 -> dynamic decision
```

------------------------------------------------------------------------

## Scenario 4 --- Existing incident

``` text
"VPN isn't working."
```

If infrastructure MCP reports an active VPN incident:

``` text
Agent
 -> check VPN
 -> active incident
 -> inform user
 -> optionally attach incident/ticket
```

It should not waste time performing unnecessary device troubleshooting.

------------------------------------------------------------------------

## Scenario 5 --- Software installation

``` text
"Install Docker."
```

Expected:

``` text
policy check
 -> authorization
 -> approval
 -> installation
 -> verification
```

------------------------------------------------------------------------

## Scenario 6 --- Access request

``` text
"I need Finance shared-drive access."
```

Expected:

``` text
check permission
 -> policy
 -> create request
 -> wait for approval
 -> resume
 -> grant
 -> verify
```

------------------------------------------------------------------------

## Scenario 7 --- Security incident

``` text
"I received an MFA request that wasn't mine."
```

Expected:

``` text
Security Agent
 -> inspect authentication
 -> inspect MFA
 -> inspect sessions
 -> security policy
 -> incident creation
 -> controlled action
```

------------------------------------------------------------------------

## Scenario 8 --- Tool failure

Simulate:

``` text
VPN service API timeout
```

Expected:

``` text
tool failure
 -> retry
 -> fallback / graceful failure
 -> no hallucinated result
```

------------------------------------------------------------------------

## Scenario 9 --- Missing information

``` text
"Install the application."
```

Expected:

``` text
Agent asks:
"Which application would you like installed?"
```

The workflow should pause and resume.

------------------------------------------------------------------------

# 47. Non-Functional Requirements

## Reliability

The agent must gracefully handle external system failures.

## Security

No sensitive action should bypass authorization.

## Maintainability

Business rules should not be embedded inside prompts where deterministic
code is more appropriate.

## Observability

Every important agent/tool operation must be traceable.

## Extensibility

Adding a new MCP capability should not require rewriting the main graph.

## Model independence

LLM provider should be configurable.

## Testability

Graph nodes and deterministic services should be independently testable.

------------------------------------------------------------------------

# 48. Important Engineering Rules

## Rule 1

Do not make everything an agent.

Use deterministic code when deterministic code is appropriate.

## Rule 2

Do not use MCP merely because it is available.

Use MCP where an external capability boundary makes sense.

## Rule 3

Do not use RAG for information that already exists reliably in
structured systems.

For example:

``` text
Employee email -> database
Device status -> MCP
Company policy -> RAG
```

## Rule 4

Do not expose raw chain-of-thought to users.

Store only useful execution metadata and concise reasoning summaries.

## Rule 5

Never trust LLM-generated authorization decisions.

Authorization must be deterministic.

## Rule 6

Never let a model directly construct unrestricted administrative
operations.

Use validated tool schemas and policy enforcement.

## Rule 7

Every tool must have clear input/output contracts.

## Rule 8

Every external operation should have timeout and error handling.

## Rule 9

Sensitive actions must be auditable.

## Rule 10

Keep the initial implementation simple.

Do not create unnecessary base classes, generic agents, generic
repositories, or abstraction layers without a concrete need.

------------------------------------------------------------------------

# 49. Definition of Done

The project is considered complete when:

-   [ ] FastAPI backend is operational.
-   [ ] React UI is operational.
-   [ ] PostgreSQL contains realistic enterprise IT data.
-   [ ] LangGraph orchestrates the support workflow.
-   [ ] At least four MCP servers are implemented.
-   [ ] Agent can dynamically select tools.
-   [ ] Agent can dynamically re-plan.
-   [ ] RAG knowledge base is operational.
-   [ ] RAG is combined with MCP tools.
-   [ ] Human approval works.
-   [ ] Long-running workflow can pause and resume.
-   [ ] Conversation state persists.
-   [ ] Tool failures are handled.
-   [ ] Retries are bounded.
-   [ ] Sensitive actions require deterministic authorization.
-   [ ] Audit logs are generated.
-   [ ] Agent execution is observable.
-   [ ] Evaluation dataset exists.
-   [ ] Evaluation metrics are generated.
-   [ ] Docker Compose starts the complete local environment.
-   [ ] At least nine demo scenarios work.
-   [ ] README explains architecture and setup.
-   [ ] Architecture documentation explains why LangGraph, MCP, RAG, and
    agents are used.

------------------------------------------------------------------------

# 50. Cursor Development Instructions

When starting implementation, do NOT generate the entire project in one
step.

Implement phase by phase.

For every phase:

1.  Inspect the existing repository.
2.  Explain the intended architecture briefly.
3.  Implement only the current phase.
4.  Add tests.
5.  Run tests.
6.  Fix errors.
7.  Update documentation.
8.  Do not prematurely implement later phases.

Maintain clean separation between:

``` text
API
Graph
Agents
MCP
RAG
Business Rules
Database
Authentication
Authorization
Observability
```

Do not introduce abstractions unless they solve a concrete problem.

Prefer readable production Python over overly clever patterns.

Use type hints.

Use environment variables for configuration and secrets.

Never hard-code credentials.

Never expose secrets in logs.

Do not expose chain-of-thought.

Use structured outputs for important agent decisions.

Validate all tool inputs.

Treat MCP tools as untrusted external dependencies that can fail.

Keep graph state explicit and minimal.

------------------------------------------------------------------------

# 51. First Implementation Task

Start with **Phase 1 only**.

Build the initial LangGraph application with:

``` text
FastAPI
  |
LangGraph
  |
Request Understanding
  |
Intent Classification
  |
Conditional Routing
  |
Response
```

Use a small set of IT support intents:

``` text
knowledge
troubleshooting
access_request
software_request
security_issue
ticket_request
unknown
```

Do NOT implement MCP, RAG, multi-agent, approval, or production
deployment in Phase 1.

The purpose of Phase 1 is to establish a clean LangGraph foundation.

After Phase 1 is working and tested, proceed to Phase 2.

------------------------------------------------------------------------

# 52. Expected Learning Outcome

At the end of the project, the developer should be able to explain and
implement:

``` text
What is an agent?
        |
        v
What is a tool?
        |
        v
Why MCP?
        |
        v
Why LangGraph?
        |
        v
Why state?
        |
        v
Why a graph instead of a simple agent loop?
        |
        v
When should an agent re-plan?
        |
        v
When should deterministic code take over?
        |
        v
How does human approval work?
        |
        v
How does a workflow survive for hours/days?
        |
        v
How do you recover from tool failures?
        |
        v
How do you evaluate an agent?
        |
        v
How do you make an agent production-safe?
```

The final system should therefore be treated as an **agentic systems
engineering project**, not merely an AI chatbot project.
