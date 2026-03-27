# CareCaller Backend — Implementation Plan

## Overview

Rewrite `carecaller-api/` as a proper backend with persistent storage, clean architecture,
and full integration with the frontend and voice agent pipeline.

### What exists today

| Layer | Status | Issues |
|---|---|---|
| Frontend (`carecaller-ui/`) | Built, has dummy API hooks | Needs real backend to call |
| Voice agent (`carecaller-agents/`) | Core pipeline works | Needs DB-enriched context |
| Backend (`carecaller-api/`) | Prototype — unstaged files | In-memory data, god object, no persistence |

### Architecture after rewrite

```
carecaller-api/
|-- main.py                         # FastAPI app, startup/shutdown, router registration
|-- config.py                       # Settings (env vars, DB path)
|
|-- db/
|   |-- __init__.py
|   |-- connection.py               # SQLite connection lifecycle (aiosqlite)
|   |-- schema.sql                  # Table definitions (single source of truth)
|   +-- seed.py                     # Seed data from transcript_samples.json
|
|-- repositories/                   # Data access — SQL queries, no business logic
|   |-- __init__.py
|   |-- patient_repo.py             # CRUD for patients + health_snapshots
|   |-- call_repo.py                # CRUD for calls + call_responses + transcript
|   +-- question_repo.py            # Read-only access to questions
|
|-- services/                       # Business logic — orchestrates repos + LLM
|   |-- __init__.py
|   |-- call_service.py             # Start/message/end call flow
|   +-- context_builder.py          # Builds LLM prompt context from DB data
|
|-- api/                            # HTTP handlers — thin, delegates to services
|   |-- __init__.py
|   |-- patients.py                 # GET /api/patients, GET /api/patients/:id
|   |-- questions.py                # GET /api/questions
|   +-- calls.py                    # POST /start, POST /:id/message, GET /:id/responses, POST /:id/end
|
|-- schemas.py                      # Pydantic request/response models (matches UI types.ts)
+-- .env.example                    # Required environment variables
```

### Key design decisions

| Decision | Choice | Reason |
|---|---|---|
| Database | SQLite via `aiosqlite` | Zero infra, microsecond latency, bundled with app, perfect for hackathon demo |
| ORM | Raw SQL (no ORM) | 4 tables, simple queries — ORM adds complexity without value at this scale |
| Architecture | Repository -> Service -> Router | Clean separation: data access / business logic / HTTP concerns |
| Session state | DB-backed (calls + call_responses) | Survives server restarts, supports call history |
| LLM context | Query DB -> format into prompt | No embeddings — data volume is low, structured data maps directly to prompt sections |
| Call state machine | Imported from `carecaller_agents.handlers.call_state` | Single source of truth — don't duplicate the FSM |

---

## Database Schema

### Table: `patients`

Core patient profile. Loaded by the API when listing patients and starting calls.

```sql
CREATE TABLE patients (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    dob         TEXT NOT NULL,
    phone       TEXT NOT NULL,
    medication  TEXT NOT NULL,
    dosage      TEXT NOT NULL,
    pharmacy    TEXT NOT NULL,
    enrolled_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Table: `health_snapshots`

Latest known health state per patient. Gives the LLM historical context
("last time you were at 233 lbs", "you mentioned no allergies").

```sql
CREATE TABLE health_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id          TEXT NOT NULL REFERENCES patients(id),
    weight_lbs          REAL,
    height              TEXT,
    goal_weight_lbs     REAL,
    weight_lost_lbs     REAL,
    side_effects        TEXT DEFAULT '',
    satisfaction        TEXT DEFAULT '',
    dosage_requests     TEXT DEFAULT '',
    new_medications     TEXT DEFAULT '',
    new_conditions      TEXT DEFAULT '',
    allergies           TEXT DEFAULT '',
    surgeries           TEXT DEFAULT '',
    doctor_questions    TEXT DEFAULT '',
    address_changed     TEXT DEFAULT '',
    snapshot_date       TEXT NOT NULL DEFAULT (date('now')),
    source_call_id      TEXT REFERENCES calls(id)
);
```

**Why one row per snapshot?** Each completed call produces a new snapshot.
The LLM gets the *latest* snapshot. Over time, you can diff snapshots to
detect trends ("you've lost 12 lbs in the last 3 months").

### Table: `calls`

One row per call attempt. Created at `POST /api/call/start`, updated at
`POST /api/call/:id/end`.

```sql
CREATE TABLE calls (
    id              TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES patients(id),
    outcome         TEXT,
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at        TEXT,
    duration_secs   REAL,
    completeness    REAL DEFAULT 0.0,
    config_tone     TEXT DEFAULT 'friendly',
    config_speed    REAL DEFAULT 1.0,
    notes           TEXT DEFAULT ''
);
```

### Table: `call_responses`

One row per question per call (14 rows for a full call). Created when the
call starts, updated as the patient answers each question.

```sql
CREATE TABLE call_responses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id             TEXT NOT NULL REFERENCES calls(id),
    question_index      INTEGER NOT NULL,
    question_text       TEXT NOT NULL,
    raw_answer          TEXT DEFAULT '',
    normalized_answer   TEXT DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'pending',
    confidence          REAL DEFAULT 0.0,
    UNIQUE(call_id, question_index)
);
```

### Table: `call_transcript`

Full conversation log for a call. Appended in real-time as the conversation
progresses.

```sql
CREATE TABLE call_transcript (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id     TEXT NOT NULL REFERENCES calls(id),
    role        TEXT NOT NULL,
    message     TEXT NOT NULL,
    timestamp   REAL NOT NULL DEFAULT 0.0
);
```

---

## Seed Data

Derived from `transcript_samples.json`. We seed 5 patients (one for each completed
call in the dataset) with their health snapshots from the call responses.

### Patients

| id | name | medication | dosage |
|---|---|---|---|
| pat_001 | Gabriella Shelton | Tirzepatide | 2.5mg weekly injection |
| pat_002 | Mrs. Kayla Travis | Tirzepatide | 5mg weekly injection |
| pat_003 | Austin Daniels | Contrave | two tablets twice daily |
| pat_004 | Shannon Miller | Tirzepatide | 5mg weekly injection |
| pat_005 | Kevin Gardner | Tirzepatide | 2.5mg weekly injection |

### Health snapshots (from completed/partial call responses)

Seeded from the answers in transcript_samples.json so the LLM has prior context
on the first call. Example for Gabriella Shelton:
- weight: 345 lbs, height: 5'6, goal: 250 lbs
- weight lost: 0, side effects: none, satisfaction: "not great but okay"
- no new meds, no conditions, no allergies, no surgeries, address unchanged

---

## LLM Context Injection

When a call starts, `context_builder.py` queries the DB and produces a structured
context block that gets injected into the system prompt:

```
PATIENT CONTEXT (from database):
  Name: Gabriella Shelton
  Medication: Tirzepatide, 2.5mg weekly injection
  Last check-in: 2026-03-15 (12 days ago)
  Last known weight: 345 lbs (goal: 250 lbs)
  Weight lost last month: 0 lbs
  Known allergies: None
  Known conditions: None
  Previous call outcome: completed (14/14 questions answered)

Use this context to personalize the conversation. Reference prior answers
when relevant (e.g., "Last time you mentioned no side effects — has that changed?").
```

This replaces the generic opening. The LLM now has *memory* of the patient.

---

## API Endpoints (matches frontend contract)

All endpoints return the exact shapes defined in `carecaller-ui/src/lib/api/types.ts`.

| Method | Path | Handler | DB Operations |
|---|---|---|---|
| GET | /api/patients | `patient_repo.list_all()` | SELECT from patients |
| GET | /api/patients/:id | `patient_repo.get_by_id()` | SELECT from patients |
| GET | /api/questions | static 14 questions | None |
| POST | /api/call/start | `call_service.start_call()` | INSERT calls + 14 call_responses, SELECT patient + snapshot |
| POST | /api/call/:id/message | `call_service.process_message()` | UPDATE call_responses, INSERT call_transcript, call Groq LLM |
| GET | /api/call/:id/responses | `call_repo.get_call_state()` | SELECT call_responses + call_transcript |
| POST | /api/call/:id/end | `call_service.end_call()` | UPDATE calls, INSERT health_snapshot (if completed) |
| GET | /health | health check | None |

### Key flow: `POST /api/call/:id/message`

```
1. call_repo.get_call(call_id)                            -- load call record
2. call_repo.get_responses(call_id)                       -- load current Q&A state
3. context_builder.build(patient_id)                      -- query DB for patient + snapshot
4. Build system prompt with context + call state
5. Build message history from call_transcript
6. Call Groq LLM (streaming)
7. Parse response: extract agent message + advance state
8. call_repo.update_response(call_id, q_index, answer)    -- persist captured answer
9. call_repo.add_transcript(call_id, "user", message)     -- persist user turn
10. call_repo.add_transcript(call_id, "agent", response)  -- persist agent turn
11. Return SendMessageResponse to UI
```

---

## Implementation Phases

### Phase 1: Database Layer

**Goal:** SQLite schema created, seeded with data, repository layer tested.

| Step | Task | File(s) |
|---|---|---|
| 1.1 | Create `config.py` with DB path + Groq settings | `config.py` |
| 1.2 | Write `schema.sql` with all 5 tables | `db/schema.sql` |
| 1.3 | Implement `connection.py` — init DB, run schema, provide connection | `db/connection.py` |
| 1.4 | Write `seed.py` — parse transcript_samples.json, insert patients + snapshots | `db/seed.py` |
| 1.5 | Implement `patient_repo.py` — list, get_by_id, get_snapshot | `repositories/patient_repo.py` |
| 1.6 | Implement `call_repo.py` — create, get, update, add_transcript, add_response | `repositories/call_repo.py` |
| 1.7 | Implement `question_repo.py` — return the 14 static questions | `repositories/question_repo.py` |
| 1.8 | Test: seed DB, query patients, verify schema | -- |

**Exit criteria:** `carecaller.db` file created with 5 patients, health snapshots,
and all tables. Repos can read/write.

### Phase 2: Service Layer

**Goal:** Business logic separated from data access. Call flow works end-to-end.

| Step | Task | File(s) |
|---|---|---|
| 2.1 | Implement `context_builder.py` — query patient + snapshot -> format for LLM | `services/context_builder.py` |
| 2.2 | Implement `call_service.py` — start_call, process_message, end_call | `services/call_service.py` |
| 2.3 | Wire call_service to use call_state from carecaller_agents (FSM) | `services/call_service.py` |
| 2.4 | Wire call_service to call Groq LLM with DB-enriched prompts | `services/call_service.py` |
| 2.5 | Test: start call -> send messages -> verify DB state updates | -- |

**Exit criteria:** Full call lifecycle works through services. Responses persisted
to DB. LLM receives patient history in its prompt.

### Phase 3: API Layer (rewrite)

**Goal:** Clean API handlers that delegate to services. Matches frontend contract exactly.

| Step | Task | File(s) |
|---|---|---|
| 3.1 | Delete old routers/, schemas, agent_bridge | cleanup |
| 3.2 | Write new `schemas.py` matching UI types.ts | `schemas.py` |
| 3.3 | Write `api/patients.py` | `api/patients.py` |
| 3.4 | Write `api/questions.py` | `api/questions.py` |
| 3.5 | Write `api/calls.py` | `api/calls.py` |
| 3.6 | Wire `main.py` — startup (init DB + seed), register routers | `main.py` |
| 3.7 | Test: all endpoints return correct response shapes | -- |

**Exit criteria:** API starts, DB initializes, all 7 endpoints work, responses
match the TypeScript types exactly.

### Phase 4: Frontend Integration

**Goal:** UI talks to real backend. Full flow works in browser.

| Step | Task | File(s) |
|---|---|---|
| 4.1 | Ensure Vite proxy config forwards /api to :8004 | `vite.config.ts` |
| 4.2 | Verify patient list loads from DB | test in browser |
| 4.3 | Verify start call -> greeting -> message loop works | test in browser |
| 4.4 | Verify response polling shows live state | test in browser |
| 4.5 | Verify end call -> summary page shows results | test in browser |
| 4.6 | Fix any UI bugs that surface during integration | `carecaller-ui/` |

**Exit criteria:** Full loop: select patient -> start call -> chat -> see responses
captured -> end call -> view summary with all data from DB.

### Phase 5: Voice Agent + DB Context

**Goal:** LiveKit voice pipeline reads patient context from DB.

| Step | Task | File(s) |
|---|---|---|
| 5.1 | API creates LiveKit room with DB-enriched patient metadata | `services/call_service.py` |
| 5.2 | Agent worker reads enriched metadata from room | `carecaller-agents/worker.py` |
| 5.3 | After voice call ends, API writes responses + snapshot to DB | `services/call_service.py` |
| 5.4 | Test: voice call through LiveKit -> DB updated | -- |

**Exit criteria:** Voice calls produce the same DB state as text calls.
Patient history accumulates across calls.

---

## Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.135.2",
    "uvicorn[standard]>=0.42.0",
    "aiosqlite>=0.20",
    "openai>=1.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0",
    "carecaller-agents",
]
```

---

## Environment Variables

```env
# Database
DB_PATH=carecaller.db

# Groq LLM
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1

# LiveKit (Phase 5)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Agent
AGENT_NAME=Jessica
LLM_TEMPERATURE=0.7
LOG_LEVEL=INFO
```
