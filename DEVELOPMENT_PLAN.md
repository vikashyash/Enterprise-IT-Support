# Enterprise IT Support Agent — Phase-wise Development Plan

> Companion to `enterprise_it_support_agent_requirements.md`.
> The requirements doc says **what** to build. This doc says **in what order, why, and how to know a phase is done**.

---

## 0. How to Read This Plan

Every phase follows the same template:

| Section | Purpose |
|---|---|
| **Goal** | One-sentence outcome of the phase |
| **Why now** | Why this phase comes at this point in the sequence |
| **You will learn** | Concepts the phase teaches |
| **Prerequisites** | What must already work |
| **Target flow** | Diagram of the runtime flow after the phase |
| **Deliverables** | Files / modules created or changed |
| **Steps** | Ordered implementation tasks |
| **State changes** | How `SupportState` evolves |
| **Tests** | What must be tested before moving on |
| **Exit criteria** | Checklist — do not start the next phase until all are true |
| **Pitfalls** | Common mistakes to avoid |

### Golden rules for every phase

1. Implement **only** the current phase. No "while I'm here" features from later phases.
2. Every phase ends with: tests passing → docs updated → commit tagged (`phase-N-complete`).
3. Deterministic code for rules (auth, policy, validation). LLM only for reasoning/language.
4. Every external call (LLM, DB, MCP, vector store) has a timeout and error handling.
5. Keep `SupportState` minimal — add a field only when a node needs it to continue the workflow.

---

## 1. The Big Picture — How the Phases Build on Each Other

```text
Phase 0  Foundation (repo, Postgres, schema, seed data, config)
   │
Phase 1  LangGraph basics ── understand → classify → route → respond
   │
Phase 2  Tool calling ────── agent calls local Python tools (DB-backed)
   │
Phase 3  MCP ─────────────── tools move out into 4 MCP servers; graph becomes MCP client
   │
Phase 4  RAG ─────────────── document ingestion + pgvector retrieval + grounded answers
   │
Phase 5  Agentic loop ────── plan → act → observe → re-plan; error recovery & retries
   │
Phase 6  Human-in-the-loop ─ policy + authz gates, interrupts, approve/reject, resume
   │
Phase 7  Durable state ───── Postgres checkpointer, conversations survive restarts,
   │                          long-running access-request workflow
Phase 8  Multi-agent ─────── supervisor + IT / Security / Access specialist subgraphs
   │
Phase 9  Observability/Eval  run logs, node transitions, tokens/cost, eval dataset & metrics
   │
Phase 10 Production hardening JWT auth, RBAC, audit, rate limit, Docker Compose, React UI
```

### Why this order?

| Order decision | Reason |
|---|---|
| DB before graph | Tools in Phase 2 need real data; seed data drives every demo scenario |
| Local tools before MCP | Learn tool-calling mechanics without transport complexity, then extract the boundary |
| RAG before agentic loop | The loop needs both capabilities (tools + knowledge) to choose between |
| Agentic loop before HITL | You can only gate actions once the agent can decide to take them |
| In-memory checkpointer (Ph 1–6) before Postgres (Ph 7) | Interrupts work in memory first; durability is a separate concern |
| Single agent before multi-agent | Multi-agent multiplies bugs; the single workflow must be stable first |
| Observability before hardening | You need visibility to debug the hardening changes |

### Capability matrix (what exists after each phase)

| Capability | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Postgres + seed data | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FastAPI `/chat` | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| LangGraph state + routing | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool calling | | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| MCP servers | | | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| RAG | | | | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Plan / re-plan loop | | | | | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Retries / error recovery | | | | | | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Policy + approvals (interrupts) | | | | | | | ✅ | ✅ | ✅ | ✅ | ✅ |
| Persistent checkpoints | | | | | | | | ✅ | ✅ | ✅ | ✅ |
| Multi-agent | | | | | | | | | ✅ | ✅ | ✅ |
| Run logs / evaluation | | | | | | | | | | ✅ | ✅ |
| JWT, RBAC, audit, Docker, UI | | | | | | | | | | | ✅ |

---

## 2. Target Repository Layout (grows over phases)

```text
Enterprise-IT-Support/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app factory            (Ph 1)
│   │   ├── config.py             # pydantic-settings              (Ph 0)
│   │   ├── api/                  # routers: chat, health, ...     (Ph 1+)
│   │   ├── graph/                # state, nodes, builder, routing (Ph 1+)
│   │   ├── agents/               # specialist subgraphs           (Ph 8)
│   │   ├── llm/                  # provider factory (Bedrock/...) (Ph 1)
│   │   ├── tools/                # local tools                    (Ph 2, removed/wrapped Ph 3)
│   │   ├── mcp_client/           # MCP client wiring              (Ph 3)
│   │   ├── rag/                  # retriever                      (Ph 4)
│   │   ├── policies/             # deterministic policy + authz   (Ph 6)
│   │   ├── db/                   # engine, session, models        (Ph 0)
│   │   ├── repositories/         # SQL access per aggregate       (Ph 2)
│   │   ├── observability/        # logging, run tracking          (Ph 9)
│   │   └── auth/                 # JWT, RBAC                      (Ph 10)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── agent/
│   └── requirements.txt
├── mcp-servers/
│   ├── common/                   # shared DB session, error types (Ph 3)
│   ├── itsm/  device/  infrastructure/  iam/
├── knowledge/                    # markdown/pdf/docx IT docs      (Ph 4)
├── scripts/
│   ├── db/schema.sql  db/seed.sql (Ph 0)
│   ├── ingest_documents.py       (Ph 4)
├── evaluation/                   # datasets, runners, reports     (Ph 9)
├── frontend/                     # React + TS                     (Ph 10)
├── docker-compose.yml            # postgres(+pgvector) first, full stack later
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── DEVELOPMENT_PLAN.md
```

---

## 3. How `SupportState` Evolves

Do **not** create the full state from the requirements doc on day one. Grow it:

| Phase | Fields added | Used by |
|---|---|---|
| 1 | `messages`, `user_id`, `conversation_id`, `request`, `intent`, `category`, `entities`, `confidence`, `final_response` | understand, classify, route, respond |
| 1 | `missing_information` | check_missing_information → ask_user |
| 2 | `tool_calls`, `tool_results` (via messages + summary list) | tool node, analyze |
| 4 | `retrieved_documents` | retrieve, respond (sources) |
| 5 | `plan`, `current_step`, `hypotheses`, `selected_hypothesis`, `resolution_status`, `retry_count`, `errors`, `iteration` | planner, executor, analyzer, replanner |
| 6 | `approval_required`, `approval_request_id`, `approval_status`, `pending_action` | policy gate, interrupt, executor |
| 8 | `active_agent`, `specialist_results` | supervisor, specialists |
| 9 | `run_id` | tracing |

Use `Annotated[list, add_messages]` for messages and `Annotated[list, operator.add]` for append-only lists (`tool_results`, `errors`) so parallel/looping nodes merge correctly.

---

## Phase 0 — Foundation: Repo, Database, Seed Data, Config

**Goal:** A runnable local Postgres with the `itsupport` schema and realistic seed data, plus a backend skeleton that can connect to it.

**Why now:** Every later phase (tools, MCP, approvals, audit) reads or writes this data. Demo scenarios are *encoded in the seed data* (outdated VPN client, low disk, missing Finance permission, degraded GitHub).

**You will learn:** schema design for agent-backed systems, idempotency keys, audit tables, config via env vars.

**Prerequisites:** Python 3.12+, Docker Desktop (or local Postgres 16), Git.

**Target flow:**

```text
docker compose up postgres
        │
        ▼
scripts/db/schema.sql  ──►  itsupport schema (tables, enums, indexes, triggers)
        │
        ▼
scripts/db/seed.sql    ──►  sample company, employees, devices, services, tickets ...
        │
        ▼
backend/app/db/session.py ──► SQLAlchemy engine reads DATABASE_URL from .env
```

**Deliverables:**

- `docker-compose.yml` with a `postgres` service using the `pgvector/pgvector:pg16` image (so Phase 4 needs no DB migration of infra).
- `scripts/db/schema.sql`, `scripts/db/seed.sql` (schema `itsupport`).
- `backend/app/config.py` — `Settings` via `pydantic-settings` (`DATABASE_URL`, `LLM_PROVIDER`, `LLM_MODEL`, `AWS_REGION`, `LOG_LEVEL`).
- `backend/app/db/session.py` — engine + session factory.
- `backend/app/db/models.py` — SQLAlchemy models mirroring the schema (only tables needed by Phase 2 initially: employees, devices, services, tickets, software).
- `.env.example` (no secrets), `.gitignore` containing `.env`.

**Steps:**

1. Create `.gitignore` (`.env`, `__pycache__`, `.venv`, `node_modules`) and `.env.example`.
2. Add `docker-compose.yml` with Postgres + volume + healthcheck.
3. Write `schema.sql`: `CREATE SCHEMA itsupport`, enums, tables from requirements §7 plus `companies`, `knowledge_documents`, `approval_requests`, `agent_executions`, `audit_logs`; FKs, unique constraints, indexes, `updated_at` triggers, `idempotency_key` columns on `tickets` and `access_requests`.
4. Write `seed.sql` with demo-scenario hooks (see table below).
5. Mount both files into `/docker-entrypoint-initdb.d/` so a fresh volume auto-initializes.
6. Create virtualenv, install `requirements.txt` (add `sqlalchemy`, `psycopg[binary]`).
7. Write `config.py` and `db/session.py`; add a tiny script/test that runs `SELECT count(*) FROM itsupport.employees`.

**Seed data → demo scenario mapping:**

| Seed fact | Enables scenario |
|---|---|
| Employee `E2001`'s laptop has 18 GB free of 512 GB | #2 Slow laptop |
| Same laptop has Cisco AnyConnect 4.10 (latest 5.1) | #3 VPN troubleshooting |
| `VPN` service row can be flipped to `MAJOR_OUTAGE` + incident | #4 Existing incident |
| `Docker Desktop`: `license_required`, `approval_required` = true | #5 Software installation |
| `E2001` has no `Finance Shared Drive` permission | #6 Access request |
| Security admin + MFA-related KB doc | #7 Security incident |
| Multiple installable software rows | #9 Missing information ("install the application") |

**Tests:**
- DB connectivity test.
- Row-count sanity test per table.
- Constraint test: inserting duplicate `idempotency_key` fails.

**Exit criteria:**
- [ ] `docker compose up -d postgres` starts healthy.
- [ ] Fresh volume auto-creates schema + seed.
- [ ] Backend connects using `DATABASE_URL` from `.env`.
- [ ] No secrets committed.

**Pitfalls:**
- Storing secrets in `.env.example` or committing `.env`.
- Over-modelling (no repositories/services yet — just the engine and models).
- Forgetting `search_path`; always qualify `itsupport.` or set it on the connection.

---

## Phase 1 — Basic LangGraph Foundation

**Goal:** `POST /chat` runs a LangGraph that understands the request, classifies intent with structured output, routes conditionally, and returns a response. No tools.

**Why now:** Establishes the graph skeleton, state contract, and LLM provider abstraction that every later phase extends.

**You will learn:** `StateGraph`, typed state, nodes, edges, `add_conditional_edges`, structured output with Pydantic, provider-independent LLM factory, `thread_id` and an in-memory checkpointer, `interrupt()` for clarification.

**Prerequisites:** Phase 0 complete; LLM credentials (Bedrock or any provider) in `.env`.

**Target flow:**

```text
POST /chat {conversation_id?, message}
        │
        ▼
   ┌─────────────────────┐
   │ understand_request  │  LLM → RequestUnderstanding (structured)
   └─────────┬───────────┘    intent, category, entities, requires_tools,
             │                requires_knowledge, is_sensitive, missing_info
             ▼
   ┌─────────────────────┐
   │ classify_request    │  deterministic: validate intent ∈ allowed set,
   └─────────┬───────────┘  low confidence → "unknown"
             ▼
   ┌──────────────────────────┐
   │ check_missing_information│
   └───────┬──────────┬───────┘
     missing│          │complete
           ▼          ▼
     ask_user    route_by_intent ──┬── knowledge        → respond_knowledge
     (interrupt)                   ├── troubleshooting  → respond_troubleshooting
           │                       ├── access_request   → respond_access
           └─ resume with answer   ├── software_request → respond_software
              → understand_request ├── security_issue   → respond_security
                                   ├── ticket_request   → respond_ticket
                                   └── unknown          → respond_fallback
                                            │
                                            ▼
                                           END
```

In Phase 1 the `respond_*` nodes only acknowledge and describe what *would* happen next (e.g. "I'll check your device and VPN status") — they are placeholders for later phases.

**Deliverables:**

- `app/graph/state.py` — `SupportState` (TypedDict or Pydantic) with Phase 1 fields.
- `app/graph/schemas.py` — `RequestUnderstanding`, `Intent` enum (`knowledge`, `troubleshooting`, `access_request`, `software_request`, `security_issue`, `ticket_request`, `unknown`).
- `app/graph/nodes/understand.py`, `classify.py`, `clarify.py`, `respond.py`.
- `app/graph/routing.py` — pure functions returning next node names.
- `app/graph/builder.py` — `build_graph(checkpointer)` compiles the graph.
- `app/llm/factory.py` — `get_chat_model()` reads `LLM_PROVIDER`/`LLM_MODEL`; Bedrock via `langchain-aws` initially. A `FakeListChatModel` path for tests.
- `app/api/chat.py` — `POST /chat`; `app/api/health.py` — `GET /health`.
- `app/main.py`.
- `app/schemas/api.py` — `ChatRequest`, `ChatResponse` (`conversation_id`, `message`, `status`, `actions`, `tickets`, `sources`).

**Steps:**

1. Define `Intent` enum and `RequestUnderstanding` Pydantic model.
2. Define `SupportState`.
3. Implement LLM factory; verify a one-line call works.
4. Implement `understand_request` using `model.with_structured_output(RequestUnderstanding)`.
5. Implement `classify_request` (deterministic validation + confidence threshold).
6. Implement `check_missing_information` and routing function.
7. Implement `ask_user` using `interrupt({"question": ...})`; resume via `Command(resume=answer)`.
8. Implement `respond_*` placeholder nodes.
9. Build graph with `InMemorySaver`; `thread_id = conversation_id`.
10. Wire `/chat`: new conversation → `invoke`; if the thread is paused at an interrupt → resume with `Command(resume=message)`. Return `status = "waiting_user"` when interrupted.
11. Write tests; run; update README with "how to run Phase 1".

**State changes:** see §3 (Phase 1 row).

**Tests:**
- Unit: routing functions for all 7 intents + missing-info branch (no LLM).
- Unit: `classify_request` downgrades low-confidence to `unknown`.
- Graph test with fake LLM: "My laptop is slow" → `troubleshooting`; "I need Finance drive access" → `access_request`.
- Graph test: "Install the application" → interrupt → resume with "Docker" → routes to `software_request`.
- API test: `/health` 200; `/chat` returns `conversation_id`.

**Exit criteria:**
- [ ] All 7 intents reachable and tested.
- [ ] Clarification pause/resume works within one process.
- [ ] LLM provider swappable via env var; tests run with no network.
- [ ] Response never includes raw chain-of-thought.

**Pitfalls:**
- Letting the LLM pick the next node directly — routing must be a deterministic function of structured state.
- Putting free-form LLM text into state "just in case".
- Coupling nodes to Bedrock-specific classes.

---

## Phase 2 — Tool Calling (Local, DB-backed)

**Goal:** The agent can call real tools that read/write Postgres, inspect results, and loop until it can answer.

**Why now:** Learn tool-calling mechanics (schemas, tool messages, loops) in-process before introducing MCP transport.

**You will learn:** `@tool` / `StructuredTool`, `bind_tools`, `ToolNode`, ReAct-style loop, tool result inspection, loop limits, input validation.

**Prerequisites:** Phase 1 complete.

**Target flow (troubleshooting / ticket branches):**

```text
route_by_intent
   │ troubleshooting / ticket_request
   ▼
┌───────────────┐   tool_calls?   ┌───────────┐
│ agent (LLM +  │ ──── yes ─────► │ tools     │
│ bound tools)  │ ◄────────────── │ (ToolNode)│
└──────┬────────┘   results       └───────────┘
       │ no tool_calls  (or max_iterations reached)
       ▼
   respond  ──► END
```

**Tools (from requirements §45 Phase 2):**

| Tool | Reads/Writes | Notes |
|---|---|---|
| `get_employee(employee_id)` | employees | Phase 2: `employee_id` comes from request context, not the LLM |
| `get_device(employee_id \| device_id)` | devices | returns active device(s) |
| `check_vpn_status()` | services, incidents | returns status + active incident if any |
| `create_ticket(title, description, category, priority)` | tickets | idempotency key = `conversation_id + category + title_hash` |

**Deliverables:**

- `app/repositories/` — `employees.py`, `devices.py`, `services.py`, `tickets.py` (plain functions, no generic base class).
- `app/tools/` — tool definitions with Pydantic arg schemas; each returns a JSON-serializable dict with `ok`/`error`.
- `app/graph/nodes/agent.py` — LLM bound to tools; `app/graph/builder.py` updated with `ToolNode` + loop edge.
- Iteration cap (e.g. `MAX_TOOL_ITERATIONS = 6`).

**Steps:**

1. Write repository functions + unit tests against the seeded DB.
2. Wrap them as tools with strict input schemas and timeouts.
3. Inject trusted context (`user_id`) into tools server-side — never trust an LLM-supplied `employee_id` for "my device".
4. Add `agent` node and `tools` node; conditional edge `tools_condition`.
5. Add iteration cap → falls through to `respond` with a graceful message.
6. Make `create_ticket` idempotent (unique constraint + "return existing" on conflict).
7. Update `/chat` response to include `actions` and `tickets`.

**Tests:**
- Unit: each tool with valid/invalid input.
- Unit: duplicate `create_ticket` returns the same ticket.
- Graph (fake LLM scripted tool calls): "VPN not working" → `get_device` → `check_vpn_status` → answer.
- Graph: iteration cap stops infinite tool loops.

**Exit criteria:**
- [ ] Agent calls tools and reasons over results.
- [ ] Tool inputs validated; invalid input returns structured error, not exception.
- [ ] `create_ticket` idempotent.
- [ ] Loop bounded.

**Pitfalls:**
- Giving the LLM a raw SQL tool.
- Returning huge DB rows to the LLM — return only fields needed.
- Trusting `employee_id` from the model.

---

## Phase 3 — MCP Servers (Capability Boundary)

**Goal:** Move all integration logic out of the backend into four MCP servers; the LangGraph app becomes an MCP client.

**Why now:** Tool semantics are proven in Phase 2; now you learn *why* a protocol boundary helps (isolation, independent deployment, reuse by other clients).

**You will learn:** MCP server/client roles, tools vs resources, transports (`stdio` for dev, streamable HTTP for services), tool discovery, contract design, treating MCP as an untrusted dependency.

**Prerequisites:** Phase 2 complete.

**Target flow:**

```text
LangGraph agent node
        │ bind_tools(mcp_tools)
        ▼
MCP client (langchain-mcp-adapters MultiServerMCPClient)
        │
  ┌─────┼──────────────┬───────────────────┐
  ▼     ▼              ▼                   ▼
mcp-itsm   mcp-device   mcp-infrastructure   mcp-iam
  │          │              │                   │
tickets    devices,      services,           permissions,
incidents  software      incidents           access_requests,
                                             software licenses
        \______________ Postgres (itsupport) ______________/
```

**Servers and tools (requirements §9–§12):**

| Server | Tools |
|---|---|
| `mcp-itsm` | `create_ticket`, `get_ticket`, `search_tickets`, `update_ticket`, `add_ticket_comment`, `close_ticket`, `search_incidents`, `get_incident` |
| `mcp-device` | `get_employee`, `get_employee_devices`, `get_device`, `get_device_status`, `get_device_network_info`, `get_installed_software`, `get_device_storage`, `get_device_performance` |
| `mcp-infrastructure` | `check_service_health`, `check_vpn_status`, `check_network_status`, `check_dns_status`, `check_sso_status`, `check_email_service`, `search_active_incidents` |
| `mcp-iam` | `get_user_permissions`, `check_user_access`, `check_software_license`, `request_access`, `request_software_installation`, `revoke_access` (sensitive tools exist but are **not exposed to the agent until Phase 6 gates them**) |

`get_device_performance` and network info are simulated (deterministic mock values derived from seed data, e.g. low free disk → high disk %).

**Deliverables:**

- `mcp-servers/common/` — DB session, standard error envelope (`{ok:false, error:{type, message, retryable}}`).
- `mcp-servers/<name>/server.py` — `FastMCP` server per capability.
- `backend/app/mcp_client/client.py` — loads server config from env, discovers tools, applies timeouts, optional allow-list per intent.
- Remove `backend/app/tools/` (or keep only as thin test doubles).

**Steps:**

1. Build `mcp-device` first; run via stdio; list tools with the MCP inspector.
2. Port the Phase 2 tools; keep identical input/output contracts.
3. Build remaining servers.
4. Implement MCP client wiring; agent binds discovered tools.
5. Add a tool allow-list per intent (e.g. troubleshooting cannot see `revoke_access`).
6. Handle "MCP server unavailable" → structured error into state.

**Tests:**
- Unit per server: call tool functions directly.
- Integration: MCP client → server → DB round trip.
- Graph: Phase 2 scenarios still pass, now through MCP.
- Failure: server not running → graceful error, no crash.

**Exit criteria:**
- [ ] Backend contains no direct SQL for integrations.
- [ ] Four servers run independently.
- [ ] Phase 2 tests pass unchanged in behavior.
- [ ] Sensitive IAM tools not reachable by the agent yet.

**Pitfalls:**
- One giant MCP server.
- Leaking DB models across the boundary instead of explicit output schemas.
- Assuming the server is always up.

---

## Phase 4 — RAG (Internal IT Knowledge)

**Goal:** Ingest IT documents into pgvector and answer company-policy questions grounded in retrieved chunks with sources.

**Why now:** The agent needs both capability types (live systems + knowledge) before it can plan between them.

**You will learn:** loading, cleaning, chunking, embeddings, vector search, metadata filtering, access-level filtering, grounding and citations, "Rule 3" (don't RAG what a DB knows).

**Prerequisites:** Phase 3 complete; pgvector extension available (Phase 0 image).

**Target flow:**

```text
Ingestion (offline)                         Retrieval (online)
───────────────────                         ──────────────────
knowledge/**/*.md|pdf|docx|txt              route: knowledge  (or requires_knowledge)
   │ load → extract → clean                       │
   ▼                                              ▼
chunk (~500–800 tokens, overlap)            retrieve(query, category, access_level≤user)
   │                                              │ top-k + score threshold
   ▼                                              ▼
embed (configurable model)                  grade relevance (optional LLM/deterministic)
   │                                              │
   ▼                                              ▼
itsupport.knowledge_chunks (pgvector)       respond_with_sources → "I don't know" if no hits
+ knowledge_documents metadata
```

**Deliverables:**

- `knowledge/` — ~10–15 realistic docs: VPN setup, Outlook sync, slow laptop, software install policy (Docker requires approval + license), password policy, access-control policy, MFA/compromise playbook, onboarding.
- `itsupport.knowledge_chunks` table (`document_id`, `chunk_index`, `content`, `embedding vector(N)`, metadata JSONB).
- `scripts/ingest_documents.py` — idempotent by `content_hash`.
- `backend/app/rag/retriever.py` — `search(query, filters, k)`.
- Graph: `retrieve` node + `respond_knowledge` uses retrieved docs; response `sources` populated.

**Steps:**

1. Write docs with front-matter metadata (`document_id`, `category`, `version`, `access_level`, `effective_date`).
2. Implement loaders/chunker; embeddings provider configurable (Bedrock Titan / local sentence-transformers).
3. Create chunk table + vector index (HNSW or IVFFlat).
4. Implement retriever with metadata + access-level filtering.
5. Add `retrieve` node; route knowledge intent through it.
6. Enforce grounding: answer only from chunks; otherwise say it's not documented and offer a ticket.
7. Optionally expose RAG as `mcp-knowledge` later — not required now.

**Tests:**
- Unit: chunker boundaries, metadata parsing, idempotent re-ingest.
- Retrieval quality: small fixed set (query → expected `document_id` in top-3).
- Graph: "What is the VPN setup process?" → answer + sources (Scenario 1).
- Graph: question with no relevant docs → no invented policy.

**Exit criteria:**
- [ ] Re-running ingestion creates no duplicates.
- [ ] Knowledge answers include sources.
- [ ] Restricted docs not retrieved for unauthorized roles.
- [ ] Scenario 1 works.

**Pitfalls:**
- Using RAG for device status or employee email.
- No score threshold → irrelevant chunks treated as truth.
- Embedding dimension mismatch when switching models (store model name in metadata).

---

## Phase 5 — Agentic Troubleshooting (Plan → Act → Observe → Re-plan)

**Goal:** Replace the simple ReAct loop with an explicit, mutable plan; the agent re-plans from tool/RAG results and recovers from failures.

**Why now:** Tools + knowledge exist; this is the core "agent, not chatbot" phase.

**You will learn:** explicit planning, mutable plans, hypothesis tracking, conditional short-circuits, loops with bounded iterations, error classification, retries with backoff, fallback paths.

**Prerequisites:** Phases 3 and 4 complete.

**Target flow (main graph, requirements §15):**

```text
check_missing_information ──complete──► create_plan
                                            │
                                            ▼
                                   ┌──► execute_step ──► (MCP tool | RAG retrieve)
                                   │        │
                                   │        ▼
                                   │   handle_result ── error? ──► classify_error
                                   │        │                         ├ retryable → retry (backoff, ≤3)
                                   │        │                         ├ invalid_input → repair args
                                   │        │                         ├ unauthorized → stop / ask user
                                   │        │                         ├ unavailable → fallback
                                   │        │                         └ fatal → ticket / graceful fail
                                   │        ▼
                                   │   analyze_result  (update hypotheses, resolution_status)
                                   │        │
                                   │   ┌────┴─────────┬──────────────┐
                                   │ resolved    more work      max iterations
                                   │   │              │              │
                                   │   ▼              ▼              ▼
                                   │ final_answer   replan     create_ticket + answer
                                   └──────────────────┘
```

**Example dynamic paths:**

```text
"VPN isn't working" (Scenario 3)              "VPN isn't working" + VPN incident (Scenario 4)
get_device → network OK → VPN service OK      check_vpn_status → active incident
→ installed software: AnyConnect outdated     → inform user + attach incident → END
→ RAG: client update policy → recommend       (skips device troubleshooting)
```

**Deliverables:**

- `app/graph/schemas.py` — `Plan`, `PlanStep` (`id`, `action`, `capability: tool|rag`, `tool_name`, `args`, `status`, `rationale_summary`), `Hypothesis`, `AnalysisResult`.
- Nodes: `create_plan`, `execute_step`, `handle_result`, `classify_error`, `analyze_result`, `replan`, `final_answer`.
- `app/graph/errors.py` — error taxonomy (`timeout`, `auth_failure`, `unauthorized`, `invalid_input`, `unavailable`, `rate_limit`, `db_error`, `duplicate`, `fatal`) + retry policy.
- Fault-injection hooks in MCP servers (env flag, e.g. `FAULT_VPN_TIMEOUT=true`) for Scenario 8.

**Steps:**

1. Define plan/hypothesis schemas (structured output).
2. `create_plan`: LLM produces steps constrained to the intent's allowed tools.
3. `execute_step`: deterministic dispatcher — validates the step against the allow-list before calling MCP/RAG.
4. `analyze_result`: LLM updates hypotheses + `resolution_status` (`resolved` | `needs_more_info` | `unresolved`).
5. `replan`: modify remaining steps; must not repeat steps already done (and respect conversation facts like "already restarted").
6. Error classification + bounded retry with exponential backoff; retry info recorded in state.
7. Iteration cap → create ticket with gathered evidence.
8. Implement Scenarios 2, 3, 4, 8.

**Tests:**
- Unit: error classifier, retry policy, step validator (rejects non-allowed tools).
- Graph: Scenarios 2, 3, 4 take different paths for the same intent.
- Failure: injected VPN timeout → retries ≤3 → fallback, no hallucinated status (Scenario 8).
- Graph: duplicate-request error does not create a second ticket.

**Exit criteria:**
- [ ] Plans change based on results (verified by tests on path, not wording).
- [ ] Unnecessary steps skipped when an incident explains the issue.
- [ ] Retries bounded and not applied to non-retryable errors.
- [ ] Scenarios 2, 3, 4, 8 pass.

**Pitfalls:**
- Fixed sequences disguised as plans.
- Letting the LLM invent tool names/args without validation.
- Unbounded loops; retrying `unauthorized` errors.

---

## Phase 6 — Human-in-the-Loop: Policy, Authorization, Approvals

**Goal:** Sensitive actions pass deterministic policy + authorization, pause the graph for human approval via `interrupt()`, and resume to execute (or abort) after approve/reject.

**Why now:** The agent can now *decide* to take actions; this phase makes those actions safe.

**You will learn:** `interrupt()` / `Command(resume=...)`, approval payload design, policy-as-code, separation of reasoning (LLM) from enforcement (code), idempotent resume.

**Prerequisites:** Phase 5 complete. Uses the in-memory checkpointer (durability comes in Phase 7).

**Target flow (requirements §13, §22):**

```text
plan step = sensitive action (e.g. install Docker)
        │
        ▼
policy_check  (deterministic: software.installation_allowed, approval_required,
        │      license available, RAG policy doc for explanation only)
        │── denied ──► explain + optional ticket ──► END
        ▼
authorization_check (deterministic RBAC: requester role, target owned by requester)
        │── denied ──► audit DENIED ──► explain ──► END
        ▼
approval_required? ── no ──► execute_action (MCP)
        │ yes
        ▼
create approval_request row (idempotent)
        │
        ▼
INTERRUPT  {approval_id, action, device, reason}
        │
   POST /approvals/{id}/approve | reject
        │
        ▼
resume ──► approved? ── yes ──► execute_action ──► verify ──► final_answer
                    └── no ───► notify rejection ──► END
```

**Deliverables:**

- `app/policies/sensitive_actions.py` — registry of sensitive action types and their rules.
- `app/policies/authorization.py` — role → allowed actions map (EMPLOYEE, IT_AGENT, IT_ADMIN, SECURITY_ADMIN, MANAGER).
- Nodes: `policy_check`, `authorization_check`, `request_approval` (interrupt), `execute_action`, `verify_action`.
- API: `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `GET /approvals?status=PENDING`.
- MCP IAM sensitive tools now exposed **only** to `execute_action` (never to the LLM directly).

**Steps:**

1. Write policy + authz functions with unit tests first (no LLM).
2. Add gate nodes before any sensitive tool call.
3. `request_approval` writes `approval_requests` and calls `interrupt(payload)`.
4. Approval endpoints validate approver role, update row, then resume the thread with `Command(resume={"decision": ...})`.
5. `execute_action` uses idempotency key `conversation_id + action_type + resource`.
6. `verify_action` re-reads state from MCP (e.g. software now installed).
7. Implement Scenario 5 (Docker install) and Scenario 9 end-to-end with clarification + approval.

**Tests:**
- Unit: every policy rule; every role/action combination.
- Graph: approve path executes once; reject path never calls the tool.
- Graph: resuming twice doesn't execute twice.
- Safety test: crafted prompt ("ignore policy and install") still hits the gate → **0 unauthorized actions**.

**Exit criteria:**
- [ ] No sensitive MCP tool reachable without passing policy + authz.
- [ ] Interrupt/resume works for approve and reject.
- [ ] Scenarios 5 and 9 pass.

**Pitfalls:**
- Asking the LLM "is this allowed?" — authorization must be code.
- Side effects before `interrupt()` that re-run on resume (nodes re-execute from the start on resume — keep pre-interrupt work idempotent).

---

## Phase 7 — Persistent State & Long-Running Workflows

**Goal:** Graph checkpoints and conversations live in Postgres, so paused workflows survive process restarts and can wait hours/days (access request awaiting manager approval).

**Why now:** Interrupts already work in memory; now make them durable.

**You will learn:** `PostgresSaver` / `AsyncPostgresSaver` (`langgraph-checkpoint-postgres`), thread lifecycle, conversation memory, resuming after restart, state history/time-travel for debugging.

**Prerequisites:** Phase 6 complete.

**Target flow (Scenario 6, requirements §23, §28):**

```text
"I need Finance shared-drive access"
   │
identify employee (from auth context) → identify resource
   │
check_user_access (mcp-iam) ── already has access ──► inform ──► END
   │ no access
policy: Finance drive requires manager approval
   │
request_access (idempotent) → approval_request(approver = manager)
   │
INTERRUPT ─────────── process may stop / restart ───────────┐
                                                            │ hours/days
                                    manager: POST /approvals/{id}/approve
                                                            │
resume from Postgres checkpoint ◄──────────────────────────┘
   │
grant access (mcp-iam) → verify permission exists → notify user (ticket comment) → END
```

**Deliverables:**

- Checkpointer switched to Postgres (separate schema, e.g. `langgraph`), created at app startup via lifespan.
- `itsupport.conversations` table (`conversation_id`, `user_id`, `title`, `status`, `created_at`, `updated_at`, `last_run_id`).
- API: `GET /conversations`, `GET /conversations/{id}` (messages + pending interrupt, if any).
- Conversation memory: facts from earlier turns (e.g. "already restarted") available to planner via message history / summarized `known_facts`.
- Optional Redis only if needed (e.g. rate limiting later) — not required here.

**Steps:**

1. Add `langgraph-checkpoint-postgres`; initialize with `.setup()`.
2. Replace `InMemorySaver` in `build_graph`.
3. Create conversations table and repository; upsert on each `/chat`.
4. Implement access-request workflow nodes (reusing Phase 6 gates).
5. Approval endpoint resumes the correct `thread_id` loaded from `approval_requests.conversation_id`.
6. Add message-history trimming/summarization to bound context size.

**Tests:**
- Integration: start workflow → kill/restart app (new graph instance) → approve → completes.
- Graph: multi-turn memory — "I already restarted" prevents the restart recommendation.
- Graph: Scenario 6 end-to-end, including rejection branch.

**Exit criteria:**
- [ ] Pending workflows survive restarts.
- [ ] Scenario 6 passes.
- [ ] Conversations listable and resumable via API.

**Pitfalls:**
- Using the same schema for checkpoints and business tables.
- Storing large blobs in state (they get checkpointed every step).

---

## Phase 8 — Multi-Agent (Supervisor + Specialists)

**Goal:** A supervisor routes requests to specialist subgraphs — IT Support, Security, Access — each with its own tool allow-list, and combines results.

**Why now:** The single-agent workflow is stable, durable, and safe; splitting it now is a refactor, not a rewrite.

**You will learn:** subgraphs, supervisor pattern, agent handoff (`Command(goto=..., graph=Command.PARENT)`), shared vs private state, agent boundaries.

**Prerequisites:** Phase 7 complete.

**Target flow:**

```text
                    ┌───────────────┐
 user request ────► │  Supervisor   │  understands overall request, picks specialist(s),
                    └──────┬────────┘  owns global state, merges results
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
 ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
 │ IT Support     │ │ Security     │ │ Access       │
 │ device, VPN,   │ │ MFA, logins, │ │ shared drive,│
 │ email, network │ │ compromise   │ │ software,    │
 │                │ │              │ │ permissions  │
 └──────┬─────────┘ └──────┬───────┘ └──────┬───────┘
        │ uses Phase 5     │ security tools  │ Phase 6/7 gates
        │ plan loop        │ + approvals     │ + approvals
        └──────────────────┴─────────────────┘
                           │
                    Supervisor merges ──► final_answer
```

**Deliverables:**

- `app/agents/it_support.py`, `security.py`, `access.py` — each a compiled subgraph with its own allowed tools.
- `app/agents/supervisor.py` — routing (structured output) + merge.
- Security tools (simulated): `get_auth_events`, `get_mfa_events`, `get_active_sessions`, `revoke_sessions` (sensitive), `create_security_incident` — add to `mcp-iam` or a new `mcp-security` if the boundary warrants it.
- Scenario 7 (suspicious MFA) implemented.

**Steps:**

1. Extract the Phase 5–7 workflow into the IT Support subgraph unchanged; verify tests.
2. Extract access workflow into the Access subgraph.
3. Build the Security subgraph and its tools; security actions always gated.
4. Build the supervisor; route by intent first (deterministic), LLM only for ambiguous/mixed requests.
5. Support handoff (e.g. IT agent detects suspicious activity → hand to Security).

**Tests:**
- All earlier scenario tests pass via supervisor.
- Routing tests: each scenario reaches the correct specialist.
- Boundary test: IT agent cannot call security/IAM sensitive tools.
- Scenario 7 end-to-end.

**Exit criteria:**
- [ ] Three specialists, enforced tool boundaries.
- [ ] Handoff works.
- [ ] Scenarios 1–9 still pass.

**Pitfalls:**
- Starting with an LLM supervisor for everything — deterministic routing where intent is clear.
- Specialists sharing every state field (keep private state private).

---

## Phase 9 — Observability & Evaluation

**Goal:** Answer "why did the agent do this?" from stored data, and measure agent quality with a repeatable evaluation suite.

**Why now:** The system is functionally complete; now make it measurable before hardening.

**You will learn:** structured logging, run/step tracing, token/cost/latency accounting, behavior-based evaluation (not string matching), regression tracking.

**Prerequisites:** Phase 8 complete.

**Target flow:**

```text
/chat ─► run_id created ─► agent_executions (RUNNING)
             │
   every node ─► graph_transitions (node, prev, next, duration, status)
   every tool ─► tool_calls log (tool, args redacted, latency, attempt, error)
   every LLM  ─► tokens in/out, model, latency, est. cost
             │
end ─► agent_executions (COMPLETED/FAILED, totals) ─► GET /agent-runs/{id}

evaluation/datasets/questions.json ─► runner ─► graph (fake or real LLM)
             │
             ▼
metrics: intent acc, tool selection acc, arg acc, retrieval hit@k,
         workflow success, hallucination, safety violations, latency, cost
             │
             ▼
evaluation/reports/<date>.md / .json
```

**Deliverables:**

- `app/observability/logging.py` — JSON structured logs with `run_id`, `conversation_id`, secret redaction.
- `app/observability/tracking.py` — LangChain callback handler / node wrapper writing `agent_executions`, `graph_transitions`, `tool_call_logs`.
- `GET /agent-runs/{id}` — timeline of nodes, tools, decisions (concise summaries, no chain-of-thought).
- `evaluation/datasets/questions.json` — start with ~30, grow to 100+ across categories (VPN, Email, Network, Hardware, Software, Access, Security, Password, Tickets, Incidents, General).
- `evaluation/runners/run_eval.py`, `evaluation/reports/`.
- Optional: LangSmith or OpenTelemetry export.

**Steps:**

1. Add structured logging + redaction.
2. Add run tracking and transition logging.
3. Add token/cost accounting (price table in config).
4. Build `/agent-runs/{id}`.
5. Write dataset with expected properties (`expected_intent`, `expected_tools`, `requires_rag`, `expected_documents`, `must_not_call`, `expects_approval`).
6. Build runner + metrics + report.
7. Record a baseline; fail CI if safety violations > 0.

**Tests:**
- Unit: redaction never logs tokens/passwords.
- Integration: one chat produces a complete run record.
- Evaluation suite runs end to end and produces a report.

**Exit criteria:**
- [ ] Every run traceable via API.
- [ ] Eval dataset ≥ 100 scenarios (may grow over this phase).
- [ ] Report includes all metrics from requirements §39.
- [ ] Safety violations = 0.

**Pitfalls:**
- Evaluating exact wording.
- Logging full tool outputs containing PII/secrets.

---

## Phase 10 — Production Hardening, Docker, Frontend

**Goal:** A secured, containerized system with JWT auth, RBAC, audit logging, rate limiting, health checks, and a minimal React UI including approval cards.

**Why now:** Everything works and is observable; harden it without changing agent behavior.

**You will learn:** JWT auth, enforcing RBAC at API and tool layers, audit design, rate limiting, secrets handling, containerization, health/readiness probes.

**Prerequisites:** Phase 9 complete.

**Target flow:**

```text
React UI ──► POST /auth/login ──► JWT (user_id, role, company_id)
   │
   ▼  Authorization: Bearer <jwt>
FastAPI middleware: auth → rate limit → request_id
   │
   ▼
/chat, /chat/stream (SSE) ──► Supervisor graph (user context from JWT, never from LLM)
   │                                │
   │                           policy + RBAC + approvals ──► MCP servers
   │                                │
   ▼                                ▼
audit_logs (who, what, tool, authz result, approval, error) — no secrets
```

**Deliverables:**

- `app/auth/` — login, JWT issue/verify, `get_current_user` dependency, role checks.
- Endpoints from requirements §41: `/auth/login`, `/chat`, `/chat/stream`, `/conversations`, `/tickets`, `/approvals/{id}/approve|reject`, `/agent-runs/{id}`, `/health`.
- Audit logging for every sensitive decision (requirements §36 fields).
- Rate limiting (Redis or in-process for dev).
- Streaming via SSE: node-level status events ("Checking your device…") using `graph.astream(stream_mode="updates")`.
- `frontend/` — React + TS: login, chat, status timeline, approval card, ticket list.
- Dockerfiles for backend, each MCP server, frontend; `docker-compose.yml` runs the full stack.
- `README.md` (setup) and `ARCHITECTURE.md` (why LangGraph, MCP, RAG, agents).

**Steps:**

1. JWT auth + `get_current_user`; remove any temporary user-id headers.
2. RBAC on API endpoints and approval actions.
3. Audit log writer used by policy/authz/execute nodes.
4. Rate limiting + request IDs + global error handler.
5. SSE streaming endpoint.
6. React UI.
7. Dockerize; health/readiness checks; compose up the full stack.
8. Final pass over Definition of Done (requirements §49).

**Tests:**
- Auth: missing/invalid/expired token rejected.
- RBAC: employee cannot approve; manager approves only their reports' requests.
- Audit: sensitive actions produce audit rows without secrets.
- E2E: all 9 demo scenarios via the UI/API in Docker Compose.

**Exit criteria:**
- [ ] `docker compose up` starts the full environment.
- [ ] All 9 demo scenarios work end to end.
- [ ] All Definition-of-Done items in the requirements doc are checked.

**Pitfalls:**
- Trusting `employee_id` from request body instead of JWT.
- Exposing internal reasoning in SSE events — stream status, not thoughts.

---

## 4. Demo Scenario → Phase Map

| # | Scenario | First working in | Key capabilities |
|---|---|---|---|
| 1 | Knowledge question (VPN setup) | Phase 4 | RAG + sources |
| 2 | Slow laptop | Phase 5 | device MCP + KB + reasoning |
| 3 | VPN troubleshooting | Phase 5 | dynamic path, outdated client |
| 4 | Existing VPN incident | Phase 5 | short-circuit on incident |
| 5 | Install Docker | Phase 6 | policy → authz → approval → install → verify |
| 6 | Finance drive access | Phase 7 | long-running, durable approval |
| 7 | Suspicious MFA | Phase 8 | security agent + gated actions |
| 8 | VPN API timeout | Phase 5 | retry → fallback, no hallucination |
| 9 | "Install the application" | Phase 1 (clarify) / Phase 6 (full) | interrupt for missing info |

---

## 5. Testing Pyramid Across Phases

```text
                  ┌────────────────┐
                  │ Evaluation     │  Ph 9+  behavior metrics over 100+ scenarios
                ┌─┴────────────────┴─┐
                │ Agent / scenario    │  Ph 1+  fixed scenarios, fake LLM scripts
              ┌─┴─────────────────────┴─┐
              │ Integration             │  Ph 3+  graph→MCP→DB, graph→RAG, approvals
            ┌─┴─────────────────────────┴─┐
            │ Unit                        │  Ph 0+  policies, authz, tools, routing, errors
            └─────────────────────────────┘
```

- Default test LLM: a fake/scripted chat model so tests are fast, deterministic, and offline.
- Mark real-LLM tests separately (e.g. `pytest -m live`).

---

## 6. Per-Phase Workflow Checklist (repeat every phase)

1. Re-read this phase's section and the matching requirements sections.
2. Inspect the repo state; confirm the previous phase's exit criteria still hold.
3. Write a short design note (in the PR/commit message or `ARCHITECTURE.md`).
4. Implement only this phase.
5. Write tests → run → fix.
6. Update `README.md` (how to run) and `ARCHITECTURE.md` (what changed and why).
7. Commit + tag `phase-N-complete`.

---

## 7. Learning Outcomes Checklist (requirements §52)

After finishing, you should be able to answer each question with an example from this codebase:

| Question | Where you learned it |
|---|---|
| What is an agent? | Phase 2, Phase 5 |
| What is a tool? | Phase 2 |
| Why MCP? | Phase 3 |
| Why LangGraph? | Phases 1, 5, 6 |
| Why state? | Phases 1, 5, 7 |
| Why a graph instead of a simple agent loop? | Phase 5 (vs Phase 2 ReAct loop) |
| When should an agent re-plan? | Phase 5 |
| When should deterministic code take over? | Phases 1 (routing), 6 (policy/authz) |
| How does human approval work? | Phase 6 |
| How does a workflow survive for hours/days? | Phase 7 |
| How do you recover from tool failures? | Phase 5 |
| How do you evaluate an agent? | Phase 9 |
| How do you make an agent production-safe? | Phases 6, 10 |
