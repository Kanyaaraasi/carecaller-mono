# CareCaller Voice Agent Simulator — UI Spec

## Chosen Direction: Option 2 — "Phone + Inspector"

Split-pane layout with retractable inspector. Left: phone-like call UI (demo-ready). Right: tabbed inspector panel (dev tooling), collapsible via drag handle or toggle.

```
┌──────────────────────────────────────────────────────────┐
│ CareCaller Studio        [patient ▼] [scenario ▼] [◑] [⚙]│
├─────────────────────────┼┤┌──────────────────────────────┤
│                         │││ Inspector              [✕]  │
│    ┌───────────────┐    │││                              │
│    │  Card          │    │││ Tabs [Responses|Config|API]  │
│    │  (phone frame) │    │││                              │
│    │               │    │││ ScrollArea                   │
│    │  ScrollArea   │    │││  Table / checklist           │
│    │  (transcript) │    │││  w/ Badge per question       │
│    │               │    │││                              │
│    │               │    │││ Progress (completeness)      │
│    │               │    │││                              │
│    │  ╭───────────╮│    │││ Collapsible (API entries)    │
│    │  │ Input     ││    │││                              │
│    │  ╰───────────╯│    ││└──────────────────────────────┤
│    │  Button Button │    ││   ← Resizable handle          │
│    └───────────────┘    ││     (drag or double-click      │
│                         ││      to collapse)              │
└─────────────────────────┴┴───────────────────────────────┘
         Phone Pane          Inspector Pane (retractable)
```

### Retractable Inspector Behavior

- **Resizable** drag handle between phone and inspector panes
- Double-click handle or click `[✕]` to collapse inspector fully — phone goes full-width (demo mode)
- Click `[⚙]` in top bar to re-open inspector
- Inspector remembers last width on reopen
- Default split: 50/50 on wide screens, inspector collapsed on mobile

---

## Views

### 1. Pre-Call — Patient Setup

Inline form inside the phone frame before a call starts. No separate page.

- Patient name (text)
- Date of birth (date)
- Medication name (text)
- Pharmacy (text)
- **[Start Call]** button

Inspector shows Config tab by default in this state.

### 2. Active Call — Phone UI (left pane)

Simulates a real phone call screen.

**Header:**
- Patient name
- Medication
- Call timer (MM:SS)
- Status dot (🟡 connecting → 🟢 in-progress → 🔴 ended)

**Body:**
- Chat bubbles — agent left, patient right
- Auto-scroll to latest message
- Subtle typing indicator when agent is "thinking"
- Inline "captured" chip below patient responses when a Q&A answer is extracted

**Footer:**
- Mic button (large, center) — toggle recording
- Mute button
- End call button (red)
- Text input fallback for typing responses when mic isn't available

### 3. Active Call — Inspector (right pane)

Tabbed panel with 3 tabs:

**[Responses] tab:**
- List of 14 questions
- Status per question: `○` pending | `⏳` asking | `✅` answered | `⊘` skipped
- Shows captured answer text next to answered questions
- Completeness progress bar at bottom (X/14)

**[Config] tab:**
- Scenario preset dropdown (happy path, opt-out, wrong number, escalation, reschedule)
- Edge case toggles:
  - ☐ Patient asks about pricing
  - ☐ Patient reports severe side effects
  - ☐ Patient wants to reschedule
  - ☐ Wrong number
  - ☐ Patient opts out midway
- Agent behavior:
  - Tone selector (friendly / neutral / formal)
  - Response speed slider (fast ↔ slow)
  - Auto-greet toggle
  - Skip already-answered questions toggle

**[API] tab:**
- Scrollable log of every API call
- Shows: method, endpoint, status, response body (collapsed), latency
- Clear button
- Example:
  ```
  POST /api/call/start       200  {call_id:"abc-123"}     120ms
  POST /api/call/message      200  {next_question:3}        89ms
  WS   /api/call/stream       ← agent_message              —
  ```

### 4. Post-Call — Summary

Phone frame shows a summary card:
- Outcome badge (completed / incomplete / opted_out / scheduled / escalated / wrong_number)
- Call duration
- Response completeness (X/14 = Y%)
- **[New Call]** button

Inspector Responses tab shows the final structured Q&A.
Inspector API tab retains the full log for review.

---

## The 14 Health Check-In Questions

| #  | Question                                                        |
|----|-----------------------------------------------------------------|
| 1  | Can you confirm your full name?                                 |
| 2  | Can you confirm your date of birth?                             |
| 3  | What is your current weight?                                    |
| 4  | Have you experienced any side effects from your medication?     |
| 5  | If yes, what side effects have you experienced?                 |
| 6  | Are you currently taking any other medications?                 |
| 7  | If yes, what other medications are you taking?                  |
| 8  | Do you have any known allergies?                                |
| 9  | If yes, what are your allergies?                                |
| 10 | Have you had any changes in your health since your last check-in? |
| 11 | If yes, what changes have you noticed?                          |
| 12 | Are you having any difficulty taking your medication as prescribed? |
| 13 | Would you like to proceed with your medication refill?          |
| 14 | Do you have any other questions or concerns?                    |

---

## API Contract (Mock Layer)

The UI calls these endpoints. Mock implementation returns fake data locally. Backend dev implements the real versions against this contract.

### `POST /api/call/start`

Start a new call session.

**Request:**
```json
{
  "patient_name": "Maria Garcia",
  "date_of_birth": "1982-03-15",
  "medication": "Metformin 500mg",
  "pharmacy": "CVS Pharmacy",
  "config": {
    "scenario": "happy_path",
    "tone": "friendly",
    "speed": 1.0,
    "auto_greet": true,
    "skip_answered": true,
    "edge_cases": []
  }
}
```

**Response:**
```json
{
  "call_id": "call_abc123",
  "status": "connecting",
  "greeting_message": "Hi Maria, this is CareCaller calling on behalf of your healthcare provider regarding your Metformin refill. Am I speaking with Maria Garcia?"
}
```

### `POST /api/call/message`

Send patient's response, get agent's next message.

**Request:**
```json
{
  "call_id": "call_abc123",
  "message": "Yes, this is Maria.",
  "timestamp": 4.2
}
```

**Response:**
```json
{
  "agent_message": "Great, thank you for confirming. What is your current weight?",
  "captured_response": {
    "question_index": 0,
    "question": "Can you confirm your full name?",
    "answer": "Maria Garcia"
  },
  "current_question_index": 2,
  "call_status": "in-progress"
}
```

### `GET /api/call/:id/responses`

Get current structured Q&A state.

**Response:**
```json
{
  "call_id": "call_abc123",
  "responses": [
    {"question_index": 0, "question": "Can you confirm your full name?", "answer": "Maria Garcia", "status": "answered"},
    {"question_index": 1, "question": "Can you confirm your date of birth?", "answer": "March 15, 1982", "status": "answered"},
    {"question_index": 2, "question": "What is your current weight?", "answer": null, "status": "asking"},
    {"question_index": 3, "question": "Have you experienced any side effects?", "answer": null, "status": "pending"}
  ],
  "completeness": 0.14
}
```

### `POST /api/call/:id/end`

End the call.

**Request:**
```json
{
  "call_id": "call_abc123",
  "reason": "completed"
}
```

**Response:**
```json
{
  "call_id": "call_abc123",
  "outcome": "completed",
  "duration_seconds": 154,
  "responses": [ ... ],
  "completeness": 1.0,
  "transcript": [
    {"role": "agent", "text": "Hi Maria...", "timestamp": 0.0},
    {"role": "user", "text": "Yes, this is Maria.", "timestamp": 3.2}
  ]
}
```

### `WebSocket /api/call/:id/stream` (optional)

Real-time streaming for voice mode. Events:

```json
{"event": "agent_speaking", "text": "partial transcript...", "is_final": false}
{"event": "user_speaking", "text": "partial transcript...", "is_final": false}
{"event": "response_captured", "question_index": 2, "answer": "165 lbs"}
{"event": "call_status", "status": "in-progress"}
```

---

## Tech Stack

- **Framework:** React 19 + TypeScript
- **Styling:** Tailwind v4 + shadcn (base-vega, remixicon)
- **Icons:** Remix Icons (@remixicon/react)
- **Build:** Vite
- **State:** React useState/useReducer (no external lib)
- **Mock layer:** Local mock API with simulated delays, swappable for real endpoints
- **Voice (future):** OpenAI Realtime API / ElevenLabs / Gemini Live — UI has hooks ready

---

## shadcn Components Used

### Layout & Structure
| Component      | Where                                                    |
|----------------|----------------------------------------------------------|
| `resizable`    | Main split pane — phone (left) + inspector (right), retractable via drag handle |
| `tabs`         | Inspector tab switching: Responses / Config / API        |
| `card`         | Phone frame, patient setup form, summary cards           |
| `scroll-area`  | Transcript panel, API log, responses list                |
| `separator`    | Section dividers within inspector tabs                   |
| `collapsible`  | API log entries — expand to see full response body       |

### Forms (Patient Setup + Config)
| Component      | Where                                                    |
|----------------|----------------------------------------------------------|
| `input`        | Patient name, medication, pharmacy                       |
| `label`        | Form field labels                                        |
| `field`        | Input + label + error wrapper                            |
| `select`       | Scenario picker, tone selector                           |
| `checkbox`     | Edge case toggles (pricing, reschedule, wrong number)    |
| `switch`       | Auto-greet toggle, skip-answered toggle                  |
| `slider`       | Response speed control                                   |
| `button`       | Start call, end call, mic toggle, new call (already installed) |

### Data Display
| Component      | Where                                                    |
|----------------|----------------------------------------------------------|
| `badge`        | Call outcome, question status (pending/asking/answered/skipped), API status codes |
| `progress`     | Response completeness bar (X/14)                         |
| `table`        | Structured Q&A in summary view + responses tab           |
| `skeleton`     | Loading states while "connecting"                        |
| `spinner`      | Agent thinking/typing indicator                          |
| `empty`        | No responses yet / no API calls yet                      |

### Extras
| Component      | Where                                                    |
|----------------|----------------------------------------------------------|
| `tooltip`      | Hover hints on call controls, config options             |
| `avatar`       | Agent/patient icons in transcript bubbles                |
| `dropdown-menu`| Patient picker in top bar                                |
| `sonner`       | Toast notifications (call started, error, edge case triggered) |
| `kbd`          | Keyboard shortcut hints (mute, end call)                 |

---

## Evaluation Criteria Mapping

| Criteria                      | Wt  | How this UI addresses it                              |
|-------------------------------|-----|-------------------------------------------------------|
| Conversation Quality (30%)    | 30% | Phone UI shows natural back-and-forth visually        |
| Response Accuracy (30%)       | 30% | Responses tab proves every answer captured correctly  |
| Edge Case Handling (20%)      | 20% | Config tab lets you trigger edge cases live in demo   |
| Technical Implementation (10%)| 10% | API log shows clean contract, mock layer is swappable |
| Demo & Presentation (10%)     | 10% | Phone UI is presentation-ready, looks like a product  |
