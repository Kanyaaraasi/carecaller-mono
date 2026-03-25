# API Contract

The UI calls these endpoints. The base URL is configured via `VITE_API_BASE_URL` (defaults to `http://localhost:8000`).

All endpoints use JSON. Types are defined in `carecaller-ui/src/lib/api/types.ts`.

---

## Patients

### `GET /api/patients`

List all patients available for calling.

**Response:**
```json
{
  "patients": [
    {
      "id": "pat_001",
      "name": "Maria Garcia",
      "date_of_birth": "1982-03-15",
      "medication": "Metformin 500mg",
      "pharmacy": "CVS Pharmacy",
      "phone": "+1-555-0101"
    }
  ]
}
```

### `GET /api/patients/:id`

Get a single patient by ID.

**Response:**
```json
{
  "id": "pat_001",
  "name": "Maria Garcia",
  "date_of_birth": "1982-03-15",
  "medication": "Metformin 500mg",
  "pharmacy": "CVS Pharmacy",
  "phone": "+1-555-0101"
}
```

---

## Questions

### `GET /api/questions`

Returns the 14 health check-in questions the agent will ask.

**Response:**
```json
{
  "questions": [
    { "index": 0, "text": "Can you confirm your full name?" },
    { "index": 1, "text": "Can you confirm your date of birth?" },
    { "index": 2, "text": "What is your current weight?" },
    { "index": 3, "text": "Have you experienced any side effects from your medication?" },
    { "index": 4, "text": "If yes, what side effects have you experienced?" },
    { "index": 5, "text": "Are you currently taking any other medications?" },
    { "index": 6, "text": "If yes, what other medications are you taking?" },
    { "index": 7, "text": "Do you have any known allergies?" },
    { "index": 8, "text": "If yes, what are your allergies?" },
    { "index": 9, "text": "Have you had any changes in your health since your last check-in?" },
    { "index": 10, "text": "If yes, what changes have you noticed?" },
    { "index": 11, "text": "Are you having any difficulty taking your medication as prescribed?" },
    { "index": 12, "text": "Would you like to proceed with your medication refill?" },
    { "index": 13, "text": "Do you have any other questions or concerns?" }
  ]
}
```

---

## Call Lifecycle

### `POST /api/call/start`

Start a new call session for a patient.

**Request:**
```json
{
  "patient_id": "pat_001",
  "config": {
    "tone": "friendly",
    "speed": 1.0,
    "auto_greet": true,
    "skip_answered": true
  }
}
```

| Field | Type | Description |
|---|---|---|
| `patient_id` | string | Patient to call |
| `config.tone` | `"friendly"` \| `"neutral"` \| `"formal"` | Agent conversation tone |
| `config.speed` | number (0.5–2.0) | Response speed multiplier |
| `config.auto_greet` | boolean | Agent greets patient automatically |
| `config.skip_answered` | boolean | Skip questions already answered |

**Response:**
```json
{
  "call_id": "call_abc123",
  "status": "connecting",
  "greeting_message": "Hi Maria, this is CareCaller calling on behalf of your healthcare provider regarding your Metformin refill. Am I speaking with Maria Garcia?"
}
```

### `POST /api/call/:callId/message`

Send patient's response, receive agent's next message.

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
    "answer": "Maria Garcia",
    "status": "answered"
  },
  "current_question_index": 2,
  "call_status": "in-progress"
}
```

| Field | Type | Description |
|---|---|---|
| `agent_message` | string | Agent's reply text |
| `captured_response` | QuestionResponse \| null | If the patient's message answered a question, this contains it |
| `current_question_index` | number | Index of the question currently being asked |
| `call_status` | CallStatus | Current call status after processing |

### `GET /api/call/:callId/responses`

Get current structured Q&A state. The UI polls this every 2 seconds during an active call.

**Response:**
```json
{
  "call_id": "call_abc123",
  "responses": [
    { "question_index": 0, "question": "Can you confirm your full name?", "answer": "Maria Garcia", "status": "answered" },
    { "question_index": 1, "question": "Can you confirm your date of birth?", "answer": "March 15, 1982", "status": "answered" },
    { "question_index": 2, "question": "What is your current weight?", "answer": null, "status": "asking" },
    { "question_index": 3, "question": "Have you experienced any side effects?", "answer": null, "status": "pending" }
  ],
  "completeness": 0.14,
  "transcript": [
    { "id": "msg_1", "role": "agent", "text": "Hi Maria...", "timestamp": 0 },
    { "id": "msg_2", "role": "user", "text": "Yes, this is Maria.", "timestamp": 3.2 }
  ],
  "outcome": null,
  "duration_seconds": null
}
```

After call ends, `outcome` and `duration_seconds` will be populated.

### `POST /api/call/:callId/end`

End the call.

**Request:**
```json
{
  "call_id": "call_abc123",
  "reason": "completed"
}
```

| Reason values | Description |
|---|---|
| `"completed"` | All questions answered |
| `"incomplete"` | Ended early |
| `"opted_out"` | Patient declined |
| `"escalated"` | Needs human agent |
| `"wrong_number"` | Wrong person reached |

**Response:**
```json
{
  "call_id": "call_abc123",
  "outcome": "completed",
  "duration_seconds": 154,
  "responses": [ ... ],
  "completeness": 1.0,
  "transcript": [ ... ]
}
```

---

## WebSocket (Optional)

### `WS /api/call/:callId/stream`

Real-time streaming for voice mode. Not required for text-based interaction — the REST endpoints above are sufficient.

**Events (server → client):**
```json
{"event": "agent_speaking", "text": "partial transcript...", "is_final": false}
{"event": "user_speaking", "text": "partial transcript...", "is_final": false}
{"event": "response_captured", "question_index": 2, "answer": "165 lbs"}
{"event": "call_status", "status": "in-progress"}
```

---

## Enums

### CallStatus
`"idle"` | `"connecting"` | `"in-progress"` | `"completed"` | `"escalated"`

### CallOutcome
`"completed"` | `"incomplete"` | `"opted_out"` | `"scheduled"` | `"escalated"` | `"wrong_number"` | `"voicemail"`

### QuestionStatus
`"pending"` | `"asking"` | `"answered"` | `"skipped"`

### Tone
`"friendly"` | `"neutral"` | `"formal"`
