<div align="center">

# CareCaller

### AI-Powered Voice Agent for Healthcare Check-In Calls

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LiveKit](https://img.shields.io/badge/LiveKit-Agents-FF4785?style=for-the-badge&logo=webrtc&logoColor=white)](https://livekit.io)
[![Groq](https://img.shields.io/badge/Groq-LLM-F55036?style=for-the-badge&logo=lightning&logoColor=white)](https://groq.com)

[![Deepgram](https://img.shields.io/badge/Deepgram-STT%20%2F%20TTS-13EF93?style=flat-square&logo=soundcloud&logoColor=white)](https://deepgram.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-4.0-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Vite](https://img.shields.io/badge/Vite-7.x-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vite.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-ML-FF6600?style=flat-square&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)

---

*Conducts natural, conversational phone calls with patients to collect structured health questionnaire responses, detect edge cases, and persist results for clinical review.*

</div>

---

## Architecture

```
                    Browser (React)
                         |
              +----------+-----------+
              |                      |
         Text Mode              Voice Mode
              |                      |
     POST /api/call/message    LiveKit Room
              |                      |
         FastAPI Server         Voice Agent
              |                      |
         Groq LLM              Groq LLM
              |               (via LiveKit)
              |                      |
              +----------+-----------+
                         |
                    SQLite Database
                  (patients, calls,
               responses, transcripts,
                 health snapshots)
```

### Monorepo Structure

```
carecaller-mono/
├── carecaller-agents/    # LiveKit voice agent (Python)
├── carecaller-api/       # FastAPI backend (Python)
├── carecaller-ui/        # React dashboard (TypeScript)
├── carecaller-ticket/    # Call quality ML classifier (Python)
├── datasets/             # 992 synthetic call dataset
└── docs/                 # Architecture & design docs
```

---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| ![LiveKit](https://img.shields.io/badge/-LiveKit-FF4785?style=flat-square&logo=webrtc&logoColor=white) | LiveKit Agents Framework | Real-time voice orchestration |
| ![Deepgram](https://img.shields.io/badge/-Deepgram-13EF93?style=flat-square&logo=soundcloud&logoColor=white) | Deepgram Nova-2 / Aura | STT (<300ms) + TTS |
| ![Groq](https://img.shields.io/badge/-Groq-F55036?style=flat-square&logo=lightning&logoColor=white) | Groq gpt-oss-120b | LLM (OpenAI-compatible) |
| ![Silero](https://img.shields.io/badge/-Silero-4A154B?style=flat-square&logo=pytorch&logoColor=white) | Silero VAD | Voice activity detection (local) |
| ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) | FastAPI + SQLAlchemy + aiosqlite | Backend API + persistence |
| ![React](https://img.shields.io/badge/-React_19-61DAFB?style=flat-square&logo=react&logoColor=black) | React + TypeScript + Tailwind + Shadcn | Frontend dashboard |
| ![Zustand](https://img.shields.io/badge/-Zustand-443E38?style=flat-square&logo=bear&logoColor=white) | Zustand + TanStack Query v5 | State management |
| ![XGBoost](https://img.shields.io/badge/-XGBoost-FF6600?style=flat-square&logo=xgboost&logoColor=white) | scikit-learn, XGBoost, LightGBM | ML call quality classifier |

---

## Features

### Voice Agent (Problem 2)
- **Natural conversation flow** with a 14-question health questionnaire
- **Context-aware responses** using patient history from the database
- **Smart response capture** with non-answer detection (handles "huh?", "what do you mean?" naturally)
- **Edge case handling**: wrong number, opt-out, reschedule, medical escalation, voicemail
- **Real-time transcript** streamed to the UI via LiveKit data channels
- **Dual mode**: text-based chat or live voice call from the same UI

### Dashboard
- Live call transcript with agent/user turns
- Response tracking panel (14 questions with status indicators)
- API log inspector for debugging
- Call summary with structured responses + full transcript
- Voice waveform visualizer
- Dark/light theme

### Call Quality Classifier (Problem 1)
- Multi-signal ensemble: structured features, transcript diff (WER), LLM-as-judge, NLI contradiction detection, conversation flow analysis
- XGBoost + LightGBM with threshold tuning for F1 optimization
- Conformal prediction (MAPIE) for uncertainty quantification

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- API keys: LiveKit, Deepgram, Groq

### 1. Backend API

```bash
cd carecaller-api
cp .env.example .env  # Add your API keys
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8004 --reload
```

### 2. Voice Agent Worker

```bash
cd carecaller-agents
cp .env.example .env  # Add your API keys
uv sync
uv run worker.py dev
```

### 3. Frontend

```bash
cd carecaller-ui
npm install
npm run dev
```

Open `http://localhost:5173` to start.

### Environment Variables

**carecaller-agents/.env**
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
DEEPGRAM_API_KEY=your-deepgram-key
GROQ_API_KEY=your-groq-key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

**carecaller-api/.env**
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
GROQ_API_KEY=your-groq-key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/patients` | List all patients |
| `GET` | `/api/patients/:id` | Get patient by ID |
| `GET` | `/api/questions` | Get the 14 health questions |
| `POST` | `/api/call/start` | Start a text-based call |
| `POST` | `/api/call/start-voice` | Start a voice call (returns LiveKit token) |
| `POST` | `/api/call/:id/message` | Send a message in text mode |
| `GET` | `/api/call/:id/responses` | Get call responses + transcript |
| `POST` | `/api/call/:id/end` | End a call |
| `POST` | `/api/call/:id/voice-event` | Agent webhook for persisting voice results |
| `GET` | `/health` | Health check |

---

## Call Flow

### Text Mode
1. Select patient from dashboard
2. Click **Start Call** (text mode)
3. Agent greets, confirms identity, checks refill interest
4. 14-question health questionnaire with real-time response capture
5. Agent closes the call
6. Summary page with structured responses + full transcript

### Voice Mode
1. Select patient, toggle to **Voice**
2. Click **Start Voice Call** (browser requests mic access)
3. LiveKit room created with DB-enriched patient context
4. Agent worker auto-joins and conducts the call via speech
5. Responses captured in real-time via data channels
6. Call ends naturally or via End Call button
7. Results persisted to DB, summary page rendered

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `patients` | Core patient profiles (5 seeded) |
| `health_snapshots` | Historical health state per patient per call |
| `calls` | Call records with outcome, duration, completeness |
| `call_responses` | 14 Q&A rows per call with raw + normalized answers |
| `call_transcript` | Full conversation log (agent/user turns) |

---

## Documentation

Detailed architecture docs are in [`/docs`](./docs/):

- [`agents-architecture.md`](./docs/agents-architecture.md) — Voice agent design, FSM, handler chain
- [`backend-implementation.md`](./docs/backend-implementation.md) — API architecture, DB schema, implementation phases
- [`api-contract.md`](./docs/api-contract.md) — Endpoint specifications
- [`ui-architecture.md`](./docs/ui-architecture.md) — Frontend state management, component hierarchy
- [`voice-integration.md`](./docs/voice-integration.md) — LiveKit integration details
- [`evaluation-criteria.md`](./docs/evaluation-criteria.md) — Hackathon judging rubric

---

## Dataset

992 synthetic healthcare check-in calls (fully AI-generated, no real patient data):

| Split | Calls | Tickets | Ticket Rate |
|-------|-------|---------|-------------|
| Train | 689 | 59 | 8.6% |
| Validation | 144 | 11 | 7.6% |
| Test | 159 | Hidden | — |

---

---

<div align="center">

**Built for the CareCaller Hackathon 2026**

[![Made with LiveKit](https://img.shields.io/badge/Voice-LiveKit-FF4785?style=flat-square)](https://livekit.io)
[![Powered by Groq](https://img.shields.io/badge/LLM-Groq-F55036?style=flat-square)](https://groq.com)
[![Speech by Deepgram](https://img.shields.io/badge/Speech-Deepgram-13EF93?style=flat-square)](https://deepgram.com)

</div>
