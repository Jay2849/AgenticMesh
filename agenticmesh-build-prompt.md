# AGENTICMESH — FULL BUILD PROMPT & TECHNICAL SPECIFICATION
### Paste this entire document into your AI coding agent (Antigravity / Claude Code / Cursor etc.) to scaffold and build the complete system end to end.

---

## 0. PROJECT SUMMARY (give this to the agent as top-level context)

Build **AgenticMesh**, a closed-loop, AI-accelerated incident triage and human-approved remediation platform for microservices. The system:

1. Runs mock microservices that emit normal traffic and can be triggered to fail.
2. Captures logs at high throughput via a Go ingestion daemon and buffers them in Redis Streams with deduplication.
3. Diagnoses failures using AST-level code pruning + vector similarity search (RAG) over historical incidents + a multi-agent LangGraph pipeline calling the Groq LLM API, producing a structured root-cause-analysis (RCA) JSON.
4. Displays the incident and AI diagnosis on a real-time Next.js dashboard, where a human engineer must explicitly approve or reject the suggested fix (this is a hard requirement — **no remediation action executes without explicit human approval**).
5. On approval, executes remediation via the Python Docker SDK (container rollback/restart) and/or opens an automated GitHub pull request with the AI-suggested code fix (the PR is opened only — it is never auto-merged; merging still requires CI + human review).
6. On rejection, the incident stays open in the queue with full diagnostic context attached — it is never silently dropped.

**Important framing constraint for the agent:** Do not describe this system as "fully autonomous self-healing." It is "AI-accelerated diagnosis with human-approved automated remediation." Every place in code comments, README, and UI copy that would imply the system acts without human consent must instead reflect that a human approval gate exists before any remediation action.

---

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────┐    logs     ┌──────────────────┐   stream   ┌──────────────────┐
│ Mock Services +  │ ─────────► │  Go Ingestion     │ ─────────► │  Upstash Redis    │
│ Traffic Generator│             │  Daemon (dedup)   │            │  Streams (buffer) │
└─────────────────┘             └──────────────────┘            └────────┬─────────┘
                                                                            │ consumer
                                                                            ▼
┌──────────────────┐  approve/reject  ┌──────────────────┐   incident   ┌──────────────────┐
│  Docker SDK       │ ◄──────────────  │  Next.js 14       │ ◄──────────  │  LangGraph Multi- │
│  Rollback Worker  │                  │  Dashboard (WS)   │   RCA JSON   │  Agent + Groq LLM │
│  + GitHub PR bot  │  ──────────────► │  Human-in-Loop UI │              │  + pgvector RAG   │
└──────────────────┘   status updates  └──────────────────┘              └────────┬─────────┘
                                                                                    │ queries
                                                                                    ▼
                                                                          ┌──────────────────┐
                                                                          │  Supabase         │
                                                                          │  Postgres +        │
                                                                          │  pgvector           │
                                                                          └──────────────────┘
```

Everything runs as one Docker Compose stack for local dev / demo.

---

## 2. TECH STACK

| Layer | Technology |
|---|---|
| Mock services | Python FastAPI (or Node/Express) |
| Traffic generator | Python script (`asyncio` + `httpx`) |
| Ingestion daemon | Go 1.22+, goroutines, buffered channels |
| Stream broker | Upstash Redis Streams |
| Diagnosis engine | Python, `ast` module, LangGraph, Groq API (`llama-3.3-70b-versatile` or similar), Supabase Python client |
| Vector DB | Supabase Postgres + `pgvector` extension |
| Dashboard | Next.js 14 (App Router), Tailwind CSS, Lucide React, native WebSocket or Socket.IO |
| Remediation engine | Python, `docker` SDK, `PyGithub` (or raw GitHub REST via `httpx`) |
| Orchestration | Docker Compose |

---

## 3. REPOSITORY STRUCTURE

```
agenticmesh/
├── docker-compose.yml
├── .env.example
├── README.md
├── mock-services/                # Phase 1 — Ankush
│   ├── auth_service.py
│   ├── payment_service.py        # contains the deliberate /crash route
│   ├── ingestion_service.py
│   ├── traffic_generator.py
│   └── Dockerfile
├── ingestion-daemon/              # Phase 2 — Jay
│   ├── main.go
│   ├── collector/
│   │   ├── reader.go
│   │   └── dedup.go
│   ├── redisclient/
│   │   └── streams.go
│   ├── go.mod
│   └── Dockerfile
├── diagnosis-engine/               # Phase 3 — Faizan
│   ├── main.py                    # Redis consumer entrypoint
│   ├── ast_pruner.py
│   ├── embeddings.py
│   ├── rag_retriever.py
│   ├── langgraph_pipeline.py
│   ├── groq_client.py
│   ├── schemas.py                 # Pydantic models / strict JSON schema
│   └── Dockerfile
├── dashboard/                      # Phase 4 — Ankush
│   ├── app/
│   │   ├── page.tsx
│   │   ├── api/ws/route.ts
│   │   └── components/
│   │       ├── IncidentQueue.tsx
│   │       ├── IncidentCard.tsx
│   │       ├── ApprovalControls.tsx
│   │       └── LiveLogStream.tsx
│   ├── lib/websocket-client.ts
│   ├── package.json
│   └── Dockerfile
├── remediation-engine/              # Phase 5 — Karan
│   ├── main.py                    # listens for approval events
│   ├── docker_actions.py
│   ├── github_pr.py
│   └── Dockerfile
└── db/
    ├── schema.sql                  # Supabase Postgres + pgvector schema
    └── seed_historical_incidents.sql
```

---

## 4. DATA CONTRACTS (JSON schemas passed between modules)

### 4.1 Raw log event (mock service → Go daemon)
```json
{
  "timestamp": "2026-09-11T10:15:32Z",
  "service": "payment-service",
  "level": "ERROR",
  "message": "ConnectionPoolExhaustedError: max pool size 20 reached",
  "stack_trace": "Traceback (most recent call last): ...",
  "route": "/crash",
  "container_id": "payment-service-1"
}
```

### 4.2 Deduplicated incident event (Go daemon → Redis Stream `incidents`)
```json
{
  "incident_id": "inc_9f2a3b",
  "fingerprint_hash": "a1b2c3d4e5f6",
  "service": "payment-service",
  "container_id": "payment-service-1",
  "occurrence_count": 1432,
  "first_seen": "2026-09-11T10:15:30Z",
  "last_seen": "2026-09-11T10:15:41Z",
  "sample_stack_trace": "...",
  "status": "NEW"
}
```

### 4.3 RCA output (diagnosis engine → Redis Pub/Sub `rca-results` → dashboard)
```json
{
  "incident_id": "inc_9f2a3b",
  "root_cause": "Database connection pool exhausted due to unclosed connections in process_refund()",
  "faulty_code_block": {
    "file": "payment_service.py",
    "function": "process_refund",
    "line_start": 142,
    "line_end": 168,
    "code_snippet": "..."
  },
  "confidence_score": 0.87,
  "similar_historical_incidents": [
    {"incident_id": "inc_1a2b3c", "similarity": 0.91, "resolution": "..."}
  ],
  "suggested_fix": {
    "type": "code_patch",
    "diff": "...unified diff...",
    "rollback_target_tag": "v2.0"
  },
  "requires_human_approval": true,
  "status": "AWAITING_APPROVAL"
}
```

### 4.4 Approval event (dashboard → remediation engine, via Redis Pub/Sub `approvals`)
```json
{
  "incident_id": "inc_9f2a3b",
  "decision": "APPROVED",
  "approved_by": "engineer_demo_user",
  "timestamp": "2026-09-11T10:16:02Z",
  "action": "ROLLBACK_CONTAINER"
}
```
`decision` is either `"APPROVED"` or `"REJECTED"`. On `"REJECTED"`, the remediation engine takes no action; the diagnosis engine (or dashboard backend) must update the incident's Postgres row to `status = "REJECTED_OPEN"` — **never** `"CLOSED"` — so it stays visible in the open queue.

### 4.5 Remediation result (remediation engine → Postgres + dashboard, via Redis Pub/Sub `remediation-status`)
```json
{
  "incident_id": "inc_9f2a3b",
  "action_taken": "ROLLBACK_CONTAINER",
  "success": true,
  "details": "Container payment-service-1 rolled back from v2.1 to v2.0, health check passed",
  "github_pr_url": "https://github.com/org/repo/pull/42",
  "resolved_at": "2026-09-11T10:16:19Z",
  "final_status": "HEALTHY"
}
```
If `success: false`, set `final_status` to `"REMEDIATION_FAILED"` (never silently mark healthy) and re-flag the incident as critical/open in the queue.

---

## 5. DATABASE SCHEMA (Supabase Postgres, `db/schema.sql`)

```sql
create extension if not exists vector;

create table services (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  current_image_tag text,
  stable_image_tag text,
  created_at timestamptz default now()
);

create table incidents (
  id uuid primary key default gen_random_uuid(),
  incident_id text unique not null,
  service_id uuid references services(id),
  fingerprint_hash text not null,
  occurrence_count int default 1,
  sample_stack_trace text,
  status text not null default 'NEW',
  -- NEW | DIAGNOSING | AWAITING_APPROVAL | APPROVED | REJECTED_OPEN | REMEDIATED | REMEDIATION_FAILED
  first_seen timestamptz,
  last_seen timestamptz,
  created_at timestamptz default now()
);

create table incident_embeddings (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  error_signature text,
  embedding vector(1536),
  created_at timestamptz default now()
);

create table rca_results (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  root_cause text,
  faulty_file text,
  faulty_function text,
  code_snippet text,
  confidence_score float,
  suggested_fix_diff text,
  rollback_target_tag text,
  created_at timestamptz default now()
);

create table approvals (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  decision text not null, -- APPROVED | REJECTED
  approved_by text,
  decided_at timestamptz default now()
);

create table remediation_log (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  action_taken text,
  success boolean,
  details text,
  github_pr_url text,
  resolved_at timestamptz
);

create index on incident_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);
```

---

## 6. PHASE-BY-PHASE BUILD INSTRUCTIONS

### PHASE 1 — Mock Services & Traffic Generator (`mock-services/`)
- Build 3 lightweight FastAPI services: `auth`, `payment`, `ingestion`. Each has a `/health` returning `200 OK`.
- `payment_service.py` must have a `/crash` route that deliberately simulates a **DB connection pool exhaustion**: open connections in a loop without closing them until the pool errors, then raise and log a realistic Python traceback.
- Add a second failure mode: `/crash/memory-leak` that grows a list unbounded in a background task until memory pressure triggers a warning log.
- `traffic_generator.py`: an `asyncio` loop that calls each service's normal endpoints every 1 second (produces steady green logs), and exposes a small CLI flag or HTTP endpoint (`POST /inject-crash?service=payment`) to trigger a crash on demand during a live demo.
- Log format must match the "Raw log event" schema (4.1) above, written to stdout (Docker captures this) or POSTed directly to the Go daemon's ingest endpoint — pick one integration method and be consistent.

### PHASE 2 — Go Ingestion Daemon (`ingestion-daemon/`)
- `main.go`: starts an HTTP listener (or reads Docker container logs via the Docker API) and spawns a worker pool of goroutines reading off a buffered channel.
- `collector/reader.go`: parses incoming raw log lines into the schema in 4.1.
- `collector/dedup.go`: computes a fingerprint hash (e.g., SHA-256 of `service + error_type + top_stack_frame`), keeps an in-memory (or Redis-backed) TTL map of hash → count. If a hash recurs within a debounce window (e.g., 5 seconds), increment `occurrence_count` instead of emitting a new incident. Emit one deduplicated incident event (schema 4.2) per unique fingerprint per debounce window.
- `redisclient/streams.go`: publishes the deduplicated incident JSON to Redis Stream `incidents` using `XADD`.
- Must be non-blocking: a slow downstream (Redis or diagnosis engine) must never block the log-reading goroutines — use a buffered channel with a sensible size and drop-with-warning (or backpressure log) if the buffer is full, rather than crashing.

### PHASE 3 — Diagnosis Engine (`diagnosis-engine/`)
- `main.py`: a Redis Streams consumer (consumer group) that reads new entries from `incidents`, and for each:
  1. Calls `ast_pruner.py` to parse the relevant service's source file using Python's `ast` module, extracting only the function (and its direct imports) implicated by the stack trace's line numbers. This becomes the "faulty_code_block."
  2. Calls `embeddings.py` to generate a vector embedding of the error signature (service + exception type + top frame) — use any available embedding model (OpenAI, Cohere, or a local sentence-transformers model — pick one and document the choice).
  3. Calls `rag_retriever.py` to run a cosine similarity query against `incident_embeddings` in Supabase (`pgvector`) and pull the top 3 similar historical incidents with their past resolutions.
  4. Calls `langgraph_pipeline.py`, a LangGraph state machine with three nodes:
     - **Triage Agent**: classifies severity and confirms this needs full RCA vs. is a known transient blip.
     - **Incident Retrieval Agent**: formats the RAG results into structured context.
     - **Root Cause Analysis Agent**: calls `groq_client.py` with a prompt containing the pruned code block + historical context, requesting a strict JSON response matching schema 4.3 (use Groq's JSON mode or a Pydantic schema + retry-on-invalid-JSON loop in `schemas.py`).
  5. Writes the RCA result to Postgres (`rca_results` table) and publishes it to Redis Pub/Sub channel `rca-results` for the dashboard to pick up over WebSocket.
- **Guardrail requirement**: if the Groq response fails JSON schema validation twice, do not guess — mark the incident `status = "DIAGNOSIS_FAILED"` and surface that plainly on the dashboard rather than presenting a malformed or hallucinated fix as valid.

### PHASE 4 — Next.js Dashboard (`dashboard/`)
- Next.js 14 App Router, dark-mode Tailwind theme, Lucide icons.
- `app/api/ws/route.ts` (or a small separate Node/Socket.IO service): subscribes to Redis Pub/Sub channels `rca-results` and `remediation-status`, forwards messages to connected browser WebSocket clients.
- `components/IncidentQueue.tsx`: lists incidents by status (`AWAITING_APPROVAL` at top, then `REJECTED_OPEN`, then `REMEDIATED` history).
- `components/IncidentCard.tsx`: shows service name, root cause (plain-language summary, not raw JSON), the faulty code snippet (syntax-highlighted), confidence score, and similar historical incidents.
- `components/ApprovalControls.tsx`: two buttons, `[APPROVE FIX]` and `[REJECT]`. On click, POSTs the approval event (schema 4.4) to a small backend endpoint that publishes it to Redis Pub/Sub channel `approvals`. **Both buttons must be present and functional — approval is never automatic.**
- `components/LiveLogStream.tsx`: a scrolling live view of raw log lines (green = normal, red = error) fed by the same WebSocket, purely for visual effect during the demo.
- On `REJECT`, the UI must visibly keep the incident in the open queue with a "Rejected — needs manual review" tag, not remove it.

### PHASE 5 — Remediation Engine (`remediation-engine/`)
- `main.py`: subscribes to Redis Pub/Sub channel `approvals`. On `decision: "APPROVED"`:
  - Calls `docker_actions.py`, which uses the Python `docker` SDK to either restart the named container or swap its image tag from the current (broken) tag to the `stable_image_tag` stored in the `services` table, then re-checks container health.
  - Calls `github_pr.py`, which uses `PyGithub` (or raw REST) to: create a new branch (`fix/incident-<id>`), commit the `suggested_fix.diff` from the RCA result onto that branch, and open a pull request. **Do not auto-merge.** The PR description must include the RCA summary and a note that it was AI-suggested and requires human code review before merge.
  - Publishes the result (schema 4.5) to Redis Pub/Sub `remediation-status` and writes to `remediation_log` in Postgres.
- If the Docker rollback's post-action health check fails, publish `success: false, final_status: "REMEDIATION_FAILED"` — do not report `HEALTHY` unless the health check actually passed.

---

## 7. ENVIRONMENT VARIABLES (`.env.example`)

```
# Redis (Upstash)
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_CONNECTION_STRING=

# Groq
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# Embeddings (choose one provider and set the matching key)
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=

# GitHub
GITHUB_TOKEN=
GITHUB_REPO=your-org/your-repo

# Docker
DOCKER_HOST=unix:///var/run/docker.sock

# Dashboard
NEXT_PUBLIC_WS_URL=ws://localhost:4000
```

---

## 8. DOCKER COMPOSE (`docker-compose.yml` — scaffold for the agent to fill in)

```yaml
version: "3.9"
services:
  mock-services:
    build: ./mock-services
    ports: ["8001:8000"]
  ingestion-daemon:
    build: ./ingestion-daemon
    depends_on: [mock-services]
    env_file: .env
  diagnosis-engine:
    build: ./diagnosis-engine
    depends_on: [ingestion-daemon]
    env_file: .env
  dashboard:
    build: ./dashboard
    ports: ["3000:3000"]
    env_file: .env
  remediation-engine:
    build: ./remediation-engine
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    env_file: .env
networks:
  default:
    driver: bridge
```

---

## 9. BUILD ORDER (tell the agent to build in this sequence, not all at once)

1. `db/schema.sql` — stand up Supabase project, run schema, seed 5–10 fake historical incidents into `incident_embeddings` (with dummy embeddings) so RAG has something to match against on day one.
2. `mock-services/` — get normal traffic + `/crash` routes working standalone, verify logs print in the expected schema.
3. `ingestion-daemon/` — consume those logs, verify dedup logic collapses a burst of identical crashes into one incident in Redis Streams (`XRANGE incidents - +` to check manually).
4. `diagnosis-engine/` — consume from Redis, run AST pruning + RAG + LangGraph + Groq, confirm a valid RCA JSON lands in Postgres and on the `rca-results` Pub/Sub channel.
5. `dashboard/` — build the UI against a **mocked** RCA payload first (hardcoded JSON) before wiring the real WebSocket, to decouple frontend work from the AI pipeline being finished.
6. Wire dashboard to the real WebSocket + Pub/Sub feed.
7. `remediation-engine/` — build against a manually-published fake `approvals` message first, verify Docker rollback and GitHub PR creation work in isolation, then wire to the real approval button.
8. Full end-to-end run: trigger `/inject-crash`, watch it flow through all 5 phases to a restored `HEALTHY` state on the dashboard. Time it with a stopwatch — do not estimate the number you'll quote.
9. Write the README using the reframed language: "AI-accelerated incident triage with human-approved automated remediation" — not "autonomous self-healing."

---

## 10. NAMING / FRAMING RULES FOR ALL GENERATED CODE COMMENTS, README, AND UI COPY

- Never describe the system as acting "autonomously" without qualifying that every remediation action requires explicit human approval.
- Never claim MTTR numbers without a clear caveat that the number reflects the diagnosis phase on a scripted demo scenario, not a general production guarantee.
- The `REJECTED_OPEN` and `REMEDIATION_FAILED` states must exist and be visibly surfaced in the UI — do not let any code path silently mark an incident resolved/healthy without a passed health check.
- GitHub PRs created by the remediation engine must never be configured to auto-merge.

---

*End of build spec. Give this whole document to your coding agent as the system/task prompt, and build phase by phase per Section 9.*
