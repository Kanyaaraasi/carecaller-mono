# CareCaller Voice Agent — Architecture & Implementation Guide

## 1. Problem Statement

Build an AI voice agent that conducts **patient medication refill check-in calls** for TrimRX. The agent must:

- Greet patients by name and confirm identity
- Ask **14 health questionnaire questions** naturally
- Handle patients who go off-script (pricing, dosage concerns, side effects)
- Correctly capture and structure all responses into `{question, answer}` pairs
- Know when to escalate vs continue
- Handle edge cases: wrong number, opt-out, reschedule, voicemail

### Evaluation Criteria

| Criteria                    | Weight | What Matters                                              |
| --------------------------- | ------ | --------------------------------------------------------- |
| Conversation Quality        | 30%    | Natural flow, appropriate responses, handles interruptions |
| Response Accuracy           | 30%    | Correctly captures all 14 questionnaire answers            |
| Edge Case Handling          | 20%    | Pricing questions, reschedules, opt-outs, escalations      |
| Technical Implementation    | 10%    | Code quality, architecture, documentation                  |
| Demo & Presentation         | 10%    | Live demo of agent handling a simulated call                |

---

## 2. The 14 Health Questions (TrimRX Check-in)

These are the exact questions the agent must walk through, derived from the `transcript_samples.json` dataset:

| #  | Question                                                        | Expected Answer Type       |
| -- | --------------------------------------------------------------- | -------------------------- |
| 1  | How have you been feeling overall?                              | Free-text (sentiment)      |
| 2  | What's your current weight in pounds?                           | Numeric (lbs)              |
| 3  | What's your height in feet and inches?                          | Numeric (ft'in)            |
| 4  | How much weight have you lost this past month in pounds?        | Numeric (lbs) or "none"    |
| 5  | Any side effects from your medication this month?               | Yes/No + description       |
| 6  | Satisfied with your rate of weight loss?                        | Yes/No + sentiment         |
| 7  | What's your goal weight in pounds?                              | Numeric (lbs)              |
| 8  | Any requests about your dosage?                                 | Yes/No + description       |
| 9  | Have you started any new medications or supplements since last month? | Yes/No + list         |
| 10 | Do you have any new medical conditions since your last check-in? | Yes/No + description      |
| 11 | Any new allergies?                                              | Yes/No + list              |
| 12 | Any surgeries since your last check-in?                         | Yes/No + description       |
| 13 | Any questions for your doctor?                                  | Yes/No + free-text         |
| 14 | Has your shipping address changed?                              | Yes/No + address           |

---

## 3. Conversation Flow Analysis

From studying the 35 sample transcripts, the call follows a predictable 4-phase structure:

### Phase 1: Opening (3 turns)
```
AGENT: "Thanks for calling TrimRX. This is Jessica. Am I speaking with {patient_name}?"
USER:  confirms or denies identity
AGENT: "Are you interested in getting your {medication}, {dosage} refill for next month?"
USER:  confirms interest
AGENT: "Do you have 2 minutes right now for a quick check-in?"
USER:  confirms availability
```

### Phase 2: Health Questionnaire (14 question-answer pairs)
```
AGENT: asks question with natural transitions ("That's good to hear!", "Got it.", etc.)
USER:  provides answer (may be brief or verbose)
-> repeat for all 14 questions
```

### Phase 3: Closing
```
AGENT: "Thank you, {patient_name}! That wraps up our check-in.
        We'll get your refill processed right away."
USER:  farewell
```

### Phase 4: Edge Case Exits (can happen at any point)

| Outcome        | Trigger                                          | Agent Behavior                                                   |
| -------------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| `wrong_number` | User denies being the named patient               | Apologize, end call gracefully                                   |
| `opted_out`    | User declines check-in or refill                  | Confirm opt-out, end call politely                               |
| `scheduled`    | User says "call me back later"                    | Offer to schedule callback, confirm time, end call               |
| `voicemail`    | No human response after opening                   | Leave voicemail message, ask to call back                        |
| `escalated`    | User has medical concern needing human attention   | Complete questions if possible, then transfer to human           |
| `incomplete`   | User hangs up or has to leave mid-call            | Save captured responses, end call                                |
| `completed`    | All 14 questions answered                         | Thank patient, confirm refill processing                         |

---

## 4. Tech Stack

### Why These Tools?

| Tool         | Role                | Why This Choice                                                           |
| ------------ | ------------------- | ------------------------------------------------------------------------- |
| **LiveKit**  | Orchestration       | Open-source real-time communication platform with a dedicated **Agents Framework** for building voice AI pipelines. Handles WebRTC, audio routing, VAD, turn-taking, and plugin architecture for STT/LLM/TTS. |
| **Deepgram** | STT + TTS           | Low-latency streaming STT (Nova-2, <300ms) and TTS (Aura). LiveKit has first-party plugin support. Free tier: $200 in credits. |
| **Silero**   | VAD                 | Voice Activity Detection model that runs locally (no API calls). Detects when the user starts/stops speaking — critical for natural turn-taking. |
| **Twilio**   | Telephony           | Provides real phone numbers and SIP trunks. Connects PSTN (real phone calls) to LiveKit rooms for the live demo. |
| **Groq**     | LLM Inference       | Ultra-low latency LLM API (~100ms TTFT). Runs `gpt-oss-20b` — fast enough for real-time voice conversation. OpenAI-compatible API, so it plugs directly into LiveKit's `livekit-plugins-openai` with a base URL swap. |

### How They Connect

```
+-------------------------------------------------------------------------+
|                         LiveKit Server (Room)                           |
|                                                                         |
|  +---------------+   +---------------+   +-----------+   +------------+ |
|  |  Silero VAD   |-->| Deepgram STT  |-->|   Groq    |-->| Deepgram   | |
|  | (local model) |   |  (streaming)  |   |gpt-oss-20b|   |    TTS     | |
|  +-------+-------+   +---------------+   +-----------+   +-----+------+ |
|          |                                                      |       |
|          |  audio in                                audio out   |       |
|  --------+------------------------------------------------------+       |
|          ^                                          |                   |
|          |    WebRTC (audio + data channels)         v                   |
+----------+------------------------------------------+-------------------+
           |                                          |
     +-----+-----+                              +----+------+
     |  Browser   |  (livekit-client SDK)        |  Twilio   |  (SIP Trunk)
     |   (UI)     |                              |  (Phone)  |
     +------------+                              +-----------+
```

**All communication runs over WebRTC.** LiveKit's Data Channels carry lightweight
JSON events (transcripts, response captures, call status) on the same WebRTC
connection that carries audio. No separate WebSocket server required.

**Data flow for a single turn:**

1. Patient speaks into phone/browser mic
2. Audio streams into the LiveKit room via WebRTC
3. **Silero VAD** detects speech start/end (determines when the patient stopped talking)
4. **Deepgram STT** transcribes the audio to text in real-time (interim + final results)
5. **LLM** receives the transcript + call state context, generates the next agent response
6. **Deepgram TTS** converts the agent response text to speech audio
7. Audio streams back to the patient via WebRTC
8. Events (transcript, response_captured) are published via **LiveKit Data Channels** on the same WebRTC connection — the UI receives them directly through `livekit-client` SDK, zero extra infra

---

## 5. Architecture

### 5.1 System Context

```
carecaller-mono/
|-- carecaller-ui/        # React frontend (already built)
|   +-- Connects to LiveKit room via WebRTC (audio + data channels)
|   +-- Receives transcript/response events via LiveKit DataPacket
|
|-- carecaller-api/       # FastAPI backend
|   +-- Manages call lifecycle (start, end, responses)
|   +-- Creates LiveKit rooms and issues participant tokens
|   +-- REST only — no WebSocket server needed
|
|-- carecaller-agents/    # Voice agent pipeline (THIS MODULE)
|   +-- LiveKit worker that joins rooms and runs the voice pipeline
|   +-- Owns: VAD -> STT -> LLM prompt building -> TTS configuration
|   +-- Owns: Call state tracking, handler interfaces
|   +-- Publishes events via LiveKit Data Channels
|
+-- datasets/             # Training data (transcript_samples.json)
```

### 5.2 Why WebRTC Data Channels Instead of WebSocket

| Concern              | WebSocket (old plan)                     | WebRTC Data Channels (new plan)           |
| -------------------- | ---------------------------------------- | ----------------------------------------- |
| Infrastructure       | Separate WS server in carecaller-api     | Piggyback on existing LiveKit connection  |
| Cost                 | Extra server, extra connections           | Zero extra infra — already have WebRTC    |
| Latency              | Additional hop (agent -> API -> browser)  | Direct (agent -> LiveKit -> browser)       |
| Reliability          | Must manage reconnection, heartbeat      | LiveKit handles all of this               |
| Implementation       | Custom WS bridge code in API             | `room.local_participant.publish_data()`   |

**How it works:**

```python
# Agent side (carecaller-agents/worker.py)
await ctx.room.local_participant.publish_data(
    payload=json.dumps({
        "event": "response_captured",
        "question_index": 5,
        "answer": "No side effects",
    }).encode(),
    topic="call_events",
)
```

```typescript
// UI side (carecaller-ui, via livekit-client)
room.on(RoomEvent.DataReceived, (payload, participant, topic) => {
  if (topic === "call_events") {
    const event = JSON.parse(new TextDecoder().decode(payload));
    // handle transcript, response_captured, call_status events
  }
});
```

### 5.3 Interaction Between Services

```
                    +------------------------------------------+
                    |              carecaller-api               |
                    |                                          |
   UI ---REST----->|  POST /api/call/start                    |
                    |    1. Create LiveKit room                |
                    |    2. Set room metadata (patient context)|
                    |    3. Generate participant token          |
                    |    4. Return {call_id, livekit_token}     |
                    |                                          |
                    |  (No WebSocket server — events go        |
                    |   through LiveKit Data Channels)          |
                    +------------------------------------------+
                                        |
                              LiveKit Server
                           (WebRTC hub for all)
                                        |
                    +------------------------------------------+
                    |            carecaller-agents              |
                    |                                          |
                    |  Worker auto-dispatched to new rooms      |
                    |    -> Reads patient context from metadata |
                    |    -> Spawns VoicePipelineAgent           |
                    |    -> Pipeline: VAD -> STT -> LLM -> TTS |
                    |    -> Publishes events via Data Channels  |
                    +------------------------------------------+
```

### 5.4 Call Lifecycle (Sequence)

```
Browser/Phone          carecaller-api           LiveKit            carecaller-agents
     |                      |                     |                       |
     |-- POST /call/start ->|                     |                       |
     |                      |-- create room ----->|                       |
     |                      |   (with patient     |                       |
     |                      |    metadata)         |                       |
     |<-- {token, url} -----|                     |------ auto-dispatch ->|
     |                      |                     |                       |
     |-- connect(token) --->|-------------------->|                       |
     |   (WebRTC join)      |                     |<-- agent joins room --|
     |                      |                     |                       |
     |   <---- agent greeting audio --------------|<-- TTS("Hi, am I     |
     |                      |                     |     speaking with..") |
     |                      |                     |                       |
     |-- patient speaks --->|-------------------->|---- audio to VAD --->|
     |                      |                     |     -> STT -> LLM    |
     |                      |                     |     -> TTS            |
     |   <---- agent audio ------------------------<-- response audio ---|
     |                      |                     |                       |
     |   <---- DataPacket: transcript ------------|<-- publish_data() ---|
     |   <---- DataPacket: response_captured -----|<-- publish_data() ---|
     |                      |                     |                       |
     |  ... (14 questions, edge cases) ...        |                       |
     |                      |                     |                       |
     |   <---- DataPacket: call_complete ---------|<-- all Qs done ------|
     |-- POST /call/end --->|                     |                       |
```

---

## 6. Code Structure — `carecaller-agents/`

```
carecaller-agents/
|
|-- pyproject.toml                          # Project metadata, dependencies, scripts
|-- .env.example                            # API keys template
|-- .python-version                         # Python 3.13
|
|-- src/
|   +-- carecaller_agents/
|       |
|       |-- __init__.py                     # Package init, version
|       |-- worker.py                       # LiveKit worker entry point
|       |-- config.py                       # Settings via pydantic-settings
|       |
|       |-- pipeline/                       # Audio pipeline components
|       |   |-- __init__.py
|       |   |-- stt.py                      # Deepgram STT provider config
|       |   |-- tts.py                      # Deepgram TTS provider config
|       |   +-- vad.py                      # Silero VAD config
|       |
|       |-- prompts/                        # LLM prompt engineering
|       |   |-- __init__.py
|       |   |-- system_prompt.py            # Dynamic system prompt builder
|       |   +-- templates.py                # Per-phase prompt templates
|       |
|       |-- handlers/                       # Conversation logic layer (see Section 9)
|       |   |-- __init__.py
|       |   |-- call_state.py               # Call state machine (FSM)
|       |   |-- response_capture.py         # Structured answer extraction [INTERFACE]
|       |   |-- escalation.py               # Escalation detection [INTERFACE]
|       |   +-- edge_cases.py               # Edge case detection [INTERFACE]
|       |
|       |-- telephony/                      # Phone integration
|       |   |-- __init__.py
|       |   +-- twilio_sip.py               # Twilio SIP trunk config
|       |
|       +-- models/                         # Data models (Pydantic)
|           |-- __init__.py
|           |-- call.py                     # Call state, outcome, config models
|           |-- patient.py                  # Patient data model
|           +-- responses.py                # Questionnaire response schema
|
+-- tests/
    |-- __init__.py
    |-- conftest.py                         # Shared fixtures
    |-- test_call_state.py                  # State machine transitions
    |-- test_response_capture.py            # Answer extraction tests
    +-- test_edge_cases.py                  # Edge case detection tests
```

---

## 7. Module Specifications

### 7.1 `worker.py` — Entry Point

The LiveKit worker process. Connects to the LiveKit server, listens for new rooms, and spawns a `VoicePipelineAgent` for each incoming call.

**Responsibilities:**
- Register as a LiveKit worker with the server
- On new room: load patient context from room metadata
- Construct the voice pipeline (VAD + STT + LLM + TTS)
- Inject the dynamic system prompt with patient context and call state
- Publish events (transcript, response_captured, call_status) via LiveKit Data Channels
- Start the agent in the room

**LiveKit Agents Framework pattern:**
```python
# Pseudocode — actual implementation will follow LiveKit SDK conventions

app = WorkerOptions(
    entrypoint_fnc=entrypoint,
    worker_type=WorkerType.ROOM,
)

async def entrypoint(ctx: JobContext):
    # 1. Load patient context from room metadata
    # 2. Initialize call state machine
    # 3. Build system prompt
    # 4. Construct pipeline: VAD -> STT -> LLM -> TTS
    # 5. Start the VoicePipelineAgent
    # 6. On each turn: publish events via Data Channels
    pass

if __name__ == "__main__":
    cli.run_app(app)
```

### 7.2 `config.py` — Configuration

Centralized settings using `pydantic-settings`. Reads from environment variables / `.env`.

**Settings:**
```
LIVEKIT_URL          — LiveKit server WebSocket URL
LIVEKIT_API_KEY      — LiveKit API key
LIVEKIT_API_SECRET   — LiveKit API secret

DEEPGRAM_API_KEY     — Deepgram API key
DEEPGRAM_STT_MODEL   — STT model (default: "nova-2")
DEEPGRAM_TTS_MODEL   — TTS voice model (default: "aura-asteria-en")
DEEPGRAM_TTS_SAMPLE_RATE — Audio sample rate (default: 24000)

TWILIO_ACCOUNT_SID   — Twilio account SID
TWILIO_AUTH_TOKEN     — Twilio auth token
TWILIO_PHONE_NUMBER   — Twilio phone number
TWILIO_SIP_DOMAIN     — Twilio SIP trunk domain

GROQ_API_KEY         — Groq API key
GROQ_MODEL           — Groq model (default: "gpt-oss-20b")
GROQ_BASE_URL        — Groq API base URL (default: "https://api.groq.com/openai/v1")
LLM_TEMPERATURE      — LLM temperature (default: 0.7)

AGENT_NAME           — Agent persona name (default: "Jessica")
LOG_LEVEL            — Logging level (default: "INFO")
```

### 7.3 `pipeline/stt.py` — Speech-to-Text

Configures Deepgram's streaming STT for the LiveKit pipeline.

**Key configuration:**
- Model: `nova-2` (best accuracy/latency tradeoff)
- Language: `en-US`
- Interim results: `enabled` (for live transcript display in UI)
- Endpointing: `300ms` (how long to wait after silence before finalizing)
- Smart formatting: `enabled` (numbers, dates, punctuation)
- Punctuation: `enabled`

### 7.4 `pipeline/tts.py` — Text-to-Speech

Configures Deepgram's TTS for the LiveKit pipeline.

**Key configuration:**
- Model: `aura-asteria-en` (natural female voice — matches "Jessica" persona)
- Sample rate: `24000` Hz
- Encoding: `linear16`

### 7.5 `pipeline/vad.py` — Voice Activity Detection

Configures Silero VAD (runs locally, no API calls).

**Key configuration:**
- Min speech duration: `250ms` (ignore very brief noises)
- Min silence duration: `500ms` (wait before considering turn complete)
- Padding: `300ms` (include audio context before/after speech)
- Threshold: `0.5` (speech detection sensitivity)

### 7.6 `prompts/system_prompt.py` — Dynamic Prompt Builder

Builds the LLM system prompt dynamically based on:
- **Patient context** (name, medication, dosage, history)
- **Current call phase** (opening, questionnaire, closing)
- **Questions already answered** (skip completed, focus on current)
- **Call configuration** (tone, speed)

This is the critical bridge between the pipeline and the LLM. The prompt instructs the LLM on:
- Its persona (Jessica from TrimRX)
- The current call state
- Which question to ask next
- How to handle off-script responses
- When to escalate
- Output format expectations

### 7.7 `prompts/templates.py` — Prompt Templates

Stores template strings for each call phase:

| Template           | Used When                          | Content                                                    |
| ------------------ | ---------------------------------- | ---------------------------------------------------------- |
| `PERSONA_BASE`     | Always (prepended to all prompts)  | Agent identity, tone, company context                      |
| `OPENING_PHASE`    | Phase 1 (greeting + identity)      | How to greet, confirm identity, ask about refill interest  |
| `QUESTIONNAIRE`    | Phase 2 (14 questions)             | Current question, previous answers, transition guidance    |
| `CLOSING_PHASE`    | Phase 3 (wrap-up)                  | How to close the call, confirm refill processing           |
| `EDGE_CASE_RULES`  | Always (appended to all prompts)   | How to handle: wrong number, opt-out, reschedule, escalation |
| `OFF_SCRIPT_RULES` | Always (appended to all prompts)   | How to handle pricing questions, dosage concerns, etc.     |

---

## 8. Handlers — Call State & Integration Interfaces

The `handlers/` directory contains the **call state machine** (built by the pipeline team) and
**interface contracts** for the response agent team. The interfaces define *what* the pipeline
expects; the response agent team provides the *implementation*.

### 8.1 `handlers/call_state.py` — Call State Machine (Pipeline Team Builds This)

A finite state machine (FSM) that tracks where the call is. The pipeline reads this to build
the right prompt; the LLM's responses advance the state.

**States:**
```
IDLE -> GREETING -> IDENTITY_CONFIRM -> REFILL_INTEREST -> AVAILABILITY_CHECK
  -> QUESTIONNAIRE (tracks current_question_index: 0..13)
  -> CLOSING -> COMPLETED

Exit states (can transition from any state):
  -> WRONG_NUMBER
  -> OPTED_OUT
  -> SCHEDULED
  -> ESCALATED
  -> INCOMPLETE
  -> VOICEMAIL
```

**State model:**
```python
# Pseudocode
class CallState:
    phase: CallPhase                    # Current phase enum
    current_question_index: int         # 0-13 during questionnaire
    responses: list[QuestionResponse]   # Captured answers
    outcome: CallOutcome | None         # Final outcome (set on exit)
    patient: PatientContext             # Patient info for this call
    transcript: list[TranscriptTurn]    # Full conversation history
    started_at: datetime
```

**Key methods:**
- `advance()` — Move to next question or phase
- `set_outcome(outcome)` — Transition to exit state
- `get_prompt_context()` — Return current state for prompt building
- `is_terminal()` — Check if call has ended

### 8.2 `handlers/response_capture.py` — Response Extraction [INTERFACE]

> **For response agent team:** This file defines the interface your implementation must satisfy.
> The pipeline calls `extract_response()` after every patient turn during the questionnaire
> phase. You provide the implementation.

**Contract:**
```python
class ResponseCaptureHandler(Protocol):
    async def extract_response(
        self,
        question: Question,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
    ) -> CapturedResponse:
        """
        Given the current question and what the patient just said,
        extract a structured answer.

        Returns:
            CapturedResponse with:
              - question_index: int
              - raw_answer: str       (verbatim patient response)
              - normalized_answer: str (cleaned value, e.g. "233" from "I'm at 233 pounds")
              - confidence: float     (0.0-1.0)
              - needs_clarification: bool
        """
        ...
```

**Where it plugs in:**
- Called from: `worker.py` — after STT finalizes a patient utterance during questionnaire phase
- Reads from: `models/responses.py` — uses `Question`, `CapturedResponse` models
- Writes to: `CallState.responses[]` — updates the response at `current_question_index`
- Triggers: `DataPacket` event `response_captured` published to the LiveKit room

**Implementation approaches (for response agent team):**
1. **LLM function-calling** — Ask the LLM to extract the answer as a structured tool call
2. **Secondary LLM pass** — Separate extraction prompt after the conversational response
3. **Regex + heuristics** — For numeric answers (weight, height), pattern matching may suffice
4. **Hybrid** — Regex for numeric fields, LLM for free-text fields

### 8.3 `handlers/escalation.py` — Escalation Detection [INTERFACE]

> **For response agent team:** This file defines the interface for detecting when a call
> needs human intervention. The pipeline calls `should_escalate()` after each patient turn.

**Contract:**
```python
class EscalationHandler(Protocol):
    async def should_escalate(
        self,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
        call_state: CallState,
    ) -> EscalationResult:
        """
        Analyze whether this call needs human intervention.

        Triggers (from transcript analysis):
          - Patient explicitly asks to speak to a person/doctor
          - Medical emergency indicators
          - Patient distress or anger
          - Questions the agent cannot safely answer

        Returns:
            EscalationResult with:
              - should_escalate: bool
              - reason: str
              - urgency: "immediate" | "after_questions"
        """
        ...
```

**Where it plugs in:**
- Called from: `worker.py` — evaluated after each patient utterance
- Reads from: `models/call.py` — uses `CallState`, `EscalationResult` models
- Writes to: `CallState.outcome` — sets `ESCALATED` if triggered
- Triggers: State machine transitions to exit state; `DataPacket` event `call_status: escalated`

**From transcript analysis:** Escalation typically happens *after* all questions are answered
when the patient has persistent medical concerns (e.g., "I really want to talk to someone about
my nausea"). The agent completes the questionnaire first, then transfers.

### 8.4 `handlers/edge_cases.py` — Edge Case Detection [INTERFACE]

> **For response agent team:** This file defines the interface for detecting non-happy-path
> scenarios. The pipeline calls `detect_edge_case()` after each patient turn, *before*
> processing the utterance as a questionnaire answer.

**Contract:**
```python
class EdgeCaseHandler(Protocol):
    async def detect_edge_case(
        self,
        patient_utterance: str,
        call_state: CallState,
    ) -> EdgeCaseResult | None:
        """
        Check if the patient's response indicates an edge case.

        Detections:
          - Wrong number: "No, this isn't {name}" / "wrong number"
          - Opt-out: "I don't want to do this" / "not interested"
          - Reschedule: "Can you call me back?" / "I'm busy"
          - Voicemail: no response after N seconds (handled by VAD timeout)

        Returns:
            None if no edge case detected, otherwise EdgeCaseResult with:
              - case_type: "wrong_number" | "opted_out" | "scheduled" | "voicemail"
              - confidence: float
              - suggested_response: str (what the agent should say)
        """
        ...
```

**Where it plugs in:**
- Called from: `worker.py` — first check after every patient utterance (before response capture)
- Reads from: `models/call.py` — uses `CallState`, `EdgeCaseResult` models
- Writes to: `CallState.outcome` — sets the appropriate exit outcome
- Triggers: State machine transitions to exit state; pipeline generates farewell via LLM

**Implementation notes (for response agent team):**
- Priority: edge case detection runs *before* response capture on each turn
- If `detect_edge_case()` returns a result, the pipeline skips response capture and transitions
  the state machine to the exit state
- The `suggested_response` field is optional — the LLM can generate its own farewell, but
  providing a suggestion helps ensure consistency with the transcript samples

---

## 9. Response Agent Integration Guide

> This section is specifically for the **response agent / output agent developer**.
> It maps every touchpoint where your code integrates with the pipeline.

### 9.1 Files You Need to Implement

| File                           | Interface Class            | Your Job                                    |
| ------------------------------ | -------------------------- | ------------------------------------------- |
| `handlers/response_capture.py` | `ResponseCaptureHandler`   | Extract structured answers from patient speech |
| `handlers/escalation.py`       | `EscalationHandler`        | Detect when to hand off to a human           |
| `handlers/edge_cases.py`       | `EdgeCaseHandler`          | Detect wrong number, opt-out, reschedule     |

### 9.2 Files You Should Read (Not Modify)

| File                           | What It Gives You                                          |
| ------------------------------ | ---------------------------------------------------------- |
| `models/responses.py`          | `Question`, `QuestionResponse`, `CapturedResponse`, `TranscriptTurn` — the data shapes your code consumes and returns |
| `models/call.py`               | `CallState`, `CallPhase`, `CallOutcome`, `EscalationResult`, `EdgeCaseResult` — state and result types |
| `models/patient.py`            | `PatientContext` — patient info available during the call  |
| `handlers/call_state.py`       | `CallState` class — you receive this as input, understand the current phase and question index |
| `prompts/templates.py`         | Prompt templates — if your LLM implementation needs to align with the persona/tone |

### 9.3 Execution Order Per Patient Turn

```
Patient speaks
     |
     v
[1] VAD detects end-of-speech
     |
     v
[2] STT finalizes transcript
     |
     v
[3] edge_cases.detect_edge_case(utterance, call_state)      <-- YOUR CODE
     |
     +-- EdgeCaseResult found? --> transition state, generate farewell, STOP
     |
     v (no edge case)
[4] response_capture.extract_response(question, utterance)   <-- YOUR CODE
     |
     v
[5] escalation.should_escalate(utterance, context, state)    <-- YOUR CODE
     |
     +-- should_escalate=True, urgency="immediate"? --> transition state, STOP
     +-- should_escalate=True, urgency="after_questions"? --> flag, continue
     |
     v
[6] LLM generates next agent response (with updated state)
     |
     v
[7] TTS speaks the response
     |
     v
[8] Publish DataPacket events (transcript, response_captured)
```

### 9.4 How to Register Your Implementation

In `worker.py`, the pipeline expects handler instances. You provide concrete classes:

```python
# Your implementation files
from carecaller_agents.handlers.response_capture import MyResponseCapture
from carecaller_agents.handlers.escalation import MyEscalationDetector
from carecaller_agents.handlers.edge_cases import MyEdgeCaseDetector

# In entrypoint()
response_handler = MyResponseCapture(llm_client=...)
escalation_handler = MyEscalationDetector(llm_client=...)
edge_case_handler = MyEdgeCaseDetector()
```

The Protocol-based interfaces mean you just need to implement classes with the right
method signatures. No inheritance required — just structural subtyping.

---

## 10. Models — Full Specification

### 10.1 `models/call.py`
```python
class CallPhase(str, Enum):
    IDLE = "idle"
    GREETING = "greeting"
    IDENTITY_CONFIRM = "identity_confirm"
    REFILL_INTEREST = "refill_interest"
    AVAILABILITY_CHECK = "availability_check"
    QUESTIONNAIRE = "questionnaire"
    CLOSING = "closing"
    COMPLETED = "completed"
    # Exit states
    WRONG_NUMBER = "wrong_number"
    OPTED_OUT = "opted_out"
    SCHEDULED = "scheduled"
    ESCALATED = "escalated"
    INCOMPLETE = "incomplete"
    VOICEMAIL = "voicemail"

class CallOutcome(str, Enum):
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    OPTED_OUT = "opted_out"
    SCHEDULED = "scheduled"
    ESCALATED = "escalated"
    WRONG_NUMBER = "wrong_number"
    VOICEMAIL = "voicemail"

class CallConfig(BaseModel):
    tone: Literal["friendly", "neutral", "formal"] = "friendly"
    speed: float = 1.0
    auto_greet: bool = True
    agent_name: str = "Jessica"

class EscalationResult(BaseModel):
    should_escalate: bool
    reason: str = ""
    urgency: Literal["immediate", "after_questions"] = "after_questions"

class EdgeCaseResult(BaseModel):
    case_type: Literal["wrong_number", "opted_out", "scheduled", "voicemail"]
    confidence: float
    suggested_response: str = ""
```

### 10.2 `models/patient.py`
```python
class PatientContext(BaseModel):
    id: str
    name: str
    date_of_birth: str
    medication: str             # e.g., "Tirzepatide"
    dosage: str                 # e.g., "2.5mg weekly injection"
    pharmacy: str
    phone: str
```

### 10.3 `models/responses.py`
```python
class QuestionStatus(str, Enum):
    PENDING = "pending"
    ASKING = "asking"
    ANSWERED = "answered"
    SKIPPED = "skipped"

class Question(BaseModel):
    index: int                  # 0-13
    text: str                   # The question text
    expected_type: str          # "numeric", "yes_no", "free_text", "yes_no_detail"

class QuestionResponse(BaseModel):
    question_index: int         # 0-13
    question: str               # The question text
    raw_answer: str = ""        # Verbatim patient response
    normalized_answer: str = "" # Cleaned/extracted value
    status: QuestionStatus = QuestionStatus.PENDING
    confidence: float = 0.0

class CapturedResponse(BaseModel):
    question_index: int
    raw_answer: str
    normalized_answer: str
    confidence: float
    needs_clarification: bool = False

class TranscriptTurn(BaseModel):
    role: Literal["agent", "user"]
    message: str
    timestamp: float            # Seconds since call start
```

---

## 11. Implementation Phases

### Phase 1: Foundation (Core Pipeline)

**Goal:** Agent joins a LiveKit room, listens to mic audio, speaks back.

| Step | Task                                              | File(s)                          |
| ---- | ------------------------------------------------- | -------------------------------- |
| 1.1  | Initialize project: pyproject.toml, .env, config  | `pyproject.toml`, `config.py`    |
| 1.2  | Define all data models                            | `models/*.py`                    |
| 1.3  | Configure Deepgram STT provider                   | `pipeline/stt.py`               |
| 1.4  | Configure Deepgram TTS provider                   | `pipeline/tts.py`               |
| 1.5  | Configure Silero VAD                              | `pipeline/vad.py`               |
| 1.6  | Build minimal system prompt (static persona)      | `prompts/templates.py`          |
| 1.7  | Wire up VoicePipelineAgent in worker              | `worker.py`                      |
| 1.8  | Test: talk to agent in browser via LiveKit         | --                               |

**Exit criteria:** You can open a browser, join a LiveKit room, speak, and the agent responds with TTS audio.

### Phase 2: Conversation Intelligence

**Goal:** Agent follows the 14-question flow with natural transitions.

| Step | Task                                              | File(s)                          |
| ---- | ------------------------------------------------- | -------------------------------- |
| 2.1  | Build call state machine with phase transitions   | `handlers/call_state.py`        |
| 2.2  | Build dynamic system prompt with state context    | `prompts/system_prompt.py`      |
| 2.3  | Write prompt templates for each phase             | `prompts/templates.py`          |
| 2.4  | Wire state machine into worker pipeline           | `worker.py`                      |
| 2.5  | Define response capture interface (stub)          | `handlers/response_capture.py`  |
| 2.6  | Publish events via LiveKit Data Channels          | `worker.py`                      |
| 2.7  | Test: agent walks through all 14 questions         | --                               |

**Exit criteria:** Agent greets by name, confirms identity, asks all 14 questions naturally, and closes the call. Events visible via LiveKit data channel.

### Phase 3: Edge Cases & Handler Interfaces

**Goal:** Agent handles all 7 outcome types gracefully.

| Step | Task                                              | File(s)                          |
| ---- | ------------------------------------------------- | -------------------------------- |
| 3.1  | Define escalation detection interface (stub)      | `handlers/escalation.py`        |
| 3.2  | Define edge case detection interface (stub)       | `handlers/edge_cases.py`        |
| 3.3  | Add edge case rules to prompt templates           | `prompts/templates.py`          |
| 3.4  | Wire edge case outcomes into state machine        | `handlers/call_state.py`        |
| 3.5  | Write tests for state transitions                 | `tests/test_call_state.py`      |
| 3.6  | Test: wrong number, opt-out, reschedule scenarios | --                               |

**Exit criteria:** Agent correctly identifies and handles all edge cases per the transcript samples.

### Phase 4: Twilio Integration

**Goal:** Real phone calls connect to the agent.

| Step | Task                                              | File(s)                          |
| ---- | ------------------------------------------------- | -------------------------------- |
| 4.1  | Configure Twilio SIP trunk for LiveKit            | `telephony/twilio_sip.py`       |
| 4.2  | Implement outbound dialing                        | `telephony/twilio_sip.py`       |
| 4.3  | Implement inbound call routing                    | `telephony/twilio_sip.py`       |
| 4.4  | Test: dial a phone number, agent picks up          | --                               |

**Exit criteria:** You can call a real phone number and the agent conducts the check-in call.

### Phase 5: API + UI Integration

**Goal:** Full end-to-end flow from UI to agent and back.

| Step | Task                                              | File(s)                        |
| ---- | ------------------------------------------------- | ------------------------------ |
| 5.1  | API creates LiveKit room on POST /call/start      | `carecaller-api/`              |
| 5.2  | Agent worker auto-joins new rooms                 | `worker.py`                    |
| 5.3  | UI listens for DataPacket events via livekit-client| `carecaller-ui/`              |
| 5.4  | Wire UI transcript display to data channel events | `carecaller-ui/`              |
| 5.5  | Test: full flow from UI to agent to UI             | --                             |

**Exit criteria:** Click "Start Call" in the UI, agent runs, transcript + responses appear live in the browser — all over WebRTC, no WebSocket needed.

---

## 12. Dependencies

```toml
[project]
name = "carecaller-agents"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    # LiveKit Agents Framework
    "livekit-agents>=1.0",
    "livekit-plugins-deepgram>=1.0",       # STT + TTS
    "livekit-plugins-silero>=1.0",          # VAD
    "livekit-plugins-openai>=1.0",          # LLM (Groq via OpenAI-compatible interface)
    "livekit>=1.0",                         # Core LiveKit SDK

    # Configuration & Models
    "pydantic>=2.0",
    "pydantic-settings>=2.0",

    # Telephony
    "twilio>=9.0",

    # Environment
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]
```

---

## 13. Environment Variables

```env
# === LiveKit ===
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# === Deepgram ===
DEEPGRAM_API_KEY=your-deepgram-key

# === Twilio ===
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_SIP_DOMAIN=your-sip-domain.pstn.twilio.com

# === LLM (Groq — OpenAI-compatible) ===
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
LLM_TEMPERATURE=0.7

# === Agent ===
AGENT_NAME=Jessica
LOG_LEVEL=INFO
```

---

## 14. Running the Agent

### Development (local)
```bash
cd carecaller-agents

# Install dependencies
uv sync

# Start LiveKit server (local, via Docker)
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  livekit/livekit-server --dev

# Run the agent worker
python -m carecaller_agents.worker dev
```

The `dev` flag tells the LiveKit worker to automatically connect to `ws://localhost:7880`
and register for room dispatch.

### Testing with browser
1. Start the LiveKit server (above)
2. Start the agent worker (above)
3. Open the LiveKit Agents Playground (or your carecaller-ui)
4. The agent auto-joins and greets you

---

## 15. Key Design Principles

1. **Pipeline owns plumbing, LLM owns thinking.** The pipeline routes audio and manages state.
   The LLM decides what to say. Clear separation.

2. **Handlers are contracts, not implementations.** `response_capture.py`, `escalation.py`,
   `edge_cases.py` define Protocol interfaces. The response agent team implements them.
   This prevents blocking between teams.

3. **State machine is the source of truth.** Every part of the system reads call state from
   `CallState`. Prompt building, response capture, event emission — all driven by the FSM.

4. **Prompts are dynamic, not static.** The system prompt changes every turn based on call
   state, answered questions, and patient context. This keeps the LLM focused and reduces
   hallucination.

5. **WebRTC everywhere.** Audio *and* events flow through the same LiveKit WebRTC connection.
   No WebSocket server, no extra infrastructure, no extra cost. Data Channels carry the
   lightweight JSON events (transcript, response_captured, call_status) alongside the audio.

6. **Zero coupling between services.** The agent doesn't call the API. The UI doesn't call the
   agent. Everything flows through LiveKit as the central hub — rooms, tracks, data channels.
