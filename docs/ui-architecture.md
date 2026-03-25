# UI Architecture

## Tech Stack

| Layer | Tool |
|---|---|
| Framework | React 19 + TypeScript |
| Build | Vite 7 |
| Styling | Tailwind CSS v4 + shadcn (base-vega style) |
| Icons | Remix Icons (`@remixicon/react`) |
| Routing | TanStack Router (code-based) |
| Server State | TanStack React Query + Axios |
| Client State | Zustand |
| URL State | nuqs (TanStack Router adapter) |
| Toasts | Sonner |

## File Structure

```
carecaller-ui/src/
├── main.tsx                    # Entry point — providers (Query, Nuqs, Theme, Tooltip, Router)
├── router.tsx                  # Route definitions
├── index.css                   # Tailwind + shadcn theme + custom keyframes
│
├── layouts/
│   └── RootLayout.tsx          # Outlet + Toaster + Router devtools
│
├── pages/
│   ├── PatientSetup.tsx        # / — Landing hero + patient list
│   ├── ActiveCall.tsx          # /call/$callId — Phone + Inspector
│   └── CallSummary.tsx         # /call/$callId/summary — Post-call report
│
├── components/
│   ├── ThemeToggle.tsx         # Dark/light mode toggle
│   ├── theme-provider.tsx      # Theme context (from shadcn)
│   ├── call/
│   │   ├── Inspector.tsx       # Right pane — tabbed (Responses/Config/API Log)
│   │   ├── ConfigTab.tsx       # Agent config controls (tone, speed, toggles)
│   │   ├── ApiLogTab.tsx       # API request/response log viewer
│   │   └── VoiceVisualizer.tsx # Animated waveform bars
│   └── ui/                     # shadcn components (24 installed)
│
├── lib/
│   ├── utils.ts                # cn() helper
│   └── api/
│       ├── client.ts           # Axios instance
│       ├── endpoints.ts        # Endpoint URL constants
│       ├── query-client.ts     # TanStack Query client
│       ├── types.ts            # All TypeScript types
│       └── hooks/
│           ├── index.ts        # Barrel export
│           ├── usePatients.ts  # GET /api/patients
│           ├── usePatient.ts   # GET /api/patients/:id
│           ├── useQuestions.ts  # GET /api/questions
│           ├── useStartCall.ts # POST /api/call/start
│           ├── useSendMessage.ts # POST /api/call/:id/message
│           ├── useCallResponses.ts # GET /api/call/:id/responses (polling)
│           └── useEndCall.ts   # POST /api/call/:id/end
│
└── stores/
    └── call-store.ts           # Zustand store for call state
```

## Routing

| Route | Page | Description |
|---|---|---|
| `/` | PatientSetup | Landing hero → patient list → select to start call |
| `/call/$callId?patientId=xyz` | ActiveCall | Resizable phone + inspector layout |
| `/call/$callId/summary` | CallSummary | Outcome, transcript, structured responses |

- `$callId` is a path param (generated client-side via `crypto.randomUUID()`)
- `patientId` is a URL search param managed by nuqs

## State Management

### Zustand (`call-store.ts`)

Single store for all call-session state:

```
CallStore
├── callId, patientId
├── callStatus (idle → connecting → in-progress → completed)
├── elapsed (seconds timer)
├── isMuted
├── transcript[] (messages with optional capturedAnswer)
├── responses[] (14 Q&A with status)
├── apiLog[] (request/response log for inspector)
├── config (tone, speed, toggles)
└── actions: initCall, setCallStatus, addTranscriptMessage,
    updateResponse, attachCapturedAnswer, logApi, etc.
```

### TanStack React Query

Used for server data fetching:
- `usePatients()` / `usePatient(id)` — patient data
- `useQuestions()` — health check-in questions
- `useCallResponses(callId)` — polls every 2s during active call

### nuqs

URL state for `patientId` search param on the call route. Keeps it in the URL so refreshing the page preserves which patient is being called.

## Component Flow

```
PatientSetup
  → user clicks "Start New Call"
  → patient list loads from API
  → user selects patient
  → navigate to /call/$callId?patientId=xyz

ActiveCall
  → store.initCall(callId, patientId)
  → usePatient(patientId) fetches patient info
  → useQuestions() fetches 14 questions → store.setResponses()
  → user clicks "Start Call" → useStartCall mutation
  → agent greeting appears in transcript
  → user types message → useSendMessage mutation
    → agent response + captured answer added to store
    → captured chip appears on user's message
  → Inspector reads from store (responses, config, apiLog)
  → user clicks "End Call" → useEndCall mutation → navigate to summary

CallSummary
  → useCallResponses(callId) fetches final state
  → renders outcome badge, duration, completeness
  → transcript review + structured responses table
```

## Inspector (Retractable Right Pane)

Built with `react-resizable-panels`. Can be:
- Dragged to resize
- Collapsed to 0 (double-click handle or click gear icon)
- Re-opened via gear icon in top bar

Three tabs:
1. **Responses** — live checklist of 14 Q&A with status icons + progress bar
2. **Config** — tone, speed, auto-greet, skip-answered toggles (disabled during active call)
3. **API Log** — every API call logged with method, endpoint, status, latency, collapsible response body
