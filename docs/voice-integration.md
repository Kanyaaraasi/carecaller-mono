# Voice Integration Guide

The UI is built with voice integration in mind but currently uses text input. The voice pipeline runs server-side using LiveKit, with the browser only handling audio I/O via WebRTC.

## Architecture

```
┌─────────────┐     WebRTC/WebSocket      ┌──────────────────────────────┐
│   Browser    │ ◄──────────────────────►  │        LiveKit Server        │
│              │     audio streams          │                              │
│  Mic → Track │                           │  ┌─────┐  ┌─────┐  ┌─────┐  │
│  Speaker ←   │                           │  │ VAD │→ │ STT │→ │ LLM │  │
│              │                           │  └─────┘  └─────┘  └─────┘  │
│  UI only     │                           │                      ↓      │
│  handles:    │                           │                   ┌─────┐   │
│  - Display   │                           │                   │ TTS │   │
│  - Controls  │  ← transcript events      │                   └─────┘   │
│  - Transcript│  ← response_captured      │                              │
└─────────────┘                            └──────────────────────────────┘
```

**The browser does NOT do STT/TTS.** It only:
- Sends mic audio to LiveKit via WebRTC
- Receives agent audio from LiveKit via WebRTC
- Receives transcript/response events via WebSocket/data channels

The full pipeline (VAD → STT → LLM → TTS) runs server-side.

## Server-Side Pipeline

```
User speaks → VAD (voice activity detection) → STT (speech-to-text)
  → LLM (generate agent response) → TTS (text-to-speech) → User hears agent
```

Each stage runs as a LiveKit agent/participant. The API server orchestrates the pipeline and emits events to the UI.

## Integration Points in the Codebase

### 1. WebSocket Endpoint

Already defined in `endpoints.ts`:

```typescript
stream: (callId: string) => `/api/call/${callId}/stream`
```

The UI connects to this for real-time events. The backend bridges LiveKit events to this WebSocket.

### 2. Events (Server → UI)

```typescript
// Transcript updates (from STT)
{ "event": "user_transcript", "text": "Yes, this is Maria.", "is_final": true }
{ "event": "agent_transcript", "text": "Great, what is your current weight?", "is_final": true }

// Partial transcripts (for live display)
{ "event": "user_transcript", "text": "Yes, this is...", "is_final": false }

// Response captured (from LLM processing)
{ "event": "response_captured", "question_index": 0, "answer": "Maria Garcia" }

// Call state changes
{ "event": "call_status", "status": "in-progress" }

// Audio state (for visualizer)
{ "event": "speaking", "who": "agent" }  // or "user" or "none"
```

### 3. ActiveCall.tsx — WebSocket Hook

Create a `useCallStream()` hook that connects to the stream endpoint and dispatches events to the Zustand store:

```typescript
// src/hooks/useCallStream.ts
function useCallStream(callId: string, enabled: boolean) {
  const store = useCallStore()

  useEffect(() => {
    if (!enabled) return
    const ws = new WebSocket(`${WS_BASE}/api/call/${callId}/stream`)

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)

      switch (event.event) {
        case "user_transcript":
          if (event.is_final) {
            store.addTranscriptMessage({
              id: crypto.randomUUID(),
              role: "user",
              text: event.text,
              timestamp: store.elapsed,
            })
          }
          break

        case "agent_transcript":
          if (event.is_final) {
            store.addTranscriptMessage({
              id: crypto.randomUUID(),
              role: "agent",
              text: event.text,
              timestamp: store.elapsed,
            })
          }
          break

        case "response_captured":
          store.updateResponse({
            question_index: event.question_index,
            question: store.responses[event.question_index].question,
            answer: event.answer,
            status: "answered",
          })
          break

        case "call_status":
          store.setCallStatus(event.status)
          break
      }
    }

    return () => ws.close()
  }, [callId, enabled])
}
```

### 4. Audio I/O via LiveKit Client SDK

```bash
npm install livekit-client
```

The browser joins a LiveKit room as a participant. The backend provides a room token via the start-call response.

```typescript
// src/hooks/useLiveKitRoom.ts
import { Room, RoomEvent, Track } from 'livekit-client'

function useLiveKitRoom(token: string | null) {
  const roomRef = useRef<Room | null>(null)

  useEffect(() => {
    if (!token) return

    const room = new Room()
    roomRef.current = room

    room.on(RoomEvent.TrackSubscribed, (track) => {
      if (track.kind === Track.Kind.Audio) {
        // Attach agent audio to a <audio> element
        const el = track.attach()
        document.body.appendChild(el)
      }
    })

    room.connect(LIVEKIT_URL, token).then(() => {
      // Publish mic track
      room.localParticipant.setMicrophoneEnabled(true)
    })

    return () => { room.disconnect() }
  }, [token])

  return roomRef
}
```

### 5. StartCallResponse — Add Room Token

The start-call API response should include a LiveKit room token:

```json
{
  "call_id": "call_abc123",
  "status": "connecting",
  "greeting_message": "Hi Maria...",
  "livekit_token": "eyJ...",
  "livekit_url": "wss://your-livekit-server.com"
}
```

The UI uses this token to join the room. Update `StartCallResponse` in `types.ts`:

```typescript
export interface StartCallResponse {
  call_id: string
  status: CallStatus
  greeting_message: string
  livekit_token?: string
  livekit_url?: string
}
```

### 6. VoiceVisualizer.tsx

Connect to actual audio levels from the LiveKit audio track:

```typescript
const analyser = audioContext.createAnalyser()
const source = audioContext.createMediaStreamSource(remoteAudioStream)
source.connect(analyser)
// Read frequency data and pass to visualizer bars
```

### 7. Mute Button

Wire to LiveKit mic track:

```typescript
room.localParticipant.setMicrophoneEnabled(!store.isMuted)
```

## Mode Switching

The UI should support both text and voice modes:

| Mode | Input | Output | When |
|---|---|---|---|
| Text | Type in input field | Read transcript | No voice API / fallback |
| Voice | Mic via LiveKit WebRTC | Speaker via LiveKit WebRTC | LiveKit token present |

ActiveCall detects which mode based on whether `livekit_token` is present in the start-call response. Text input remains visible as fallback even in voice mode.

## Files to Create

```
src/hooks/
├── useCallStream.ts     # WebSocket for transcript/response events
└── useLiveKitRoom.ts    # LiveKit WebRTC audio I/O
```

## Backend Responsibilities

The API server handles:
1. Creating a LiveKit room when a call starts
2. Spawning the voice pipeline agents (VAD, STT, LLM, TTS) in the room
3. Bridging pipeline events to the UI WebSocket (`/api/call/:id/stream`)
4. Processing captured responses and updating call state
5. Returning a LiveKit participant token to the UI

The UI does **not** run any AI/ML — it's a thin audio I/O + display layer.
