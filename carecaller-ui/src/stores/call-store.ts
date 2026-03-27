import { create } from "zustand"
import type {
  CallStatus,
  CallConfig,
  TranscriptMessage,
  QuestionResponse,
  ApiLogEntry,
} from "@/lib/api/types"

interface CallStore {
  // Call state
  callId: string | null
  patientId: string | null
  callStatus: CallStatus
  elapsed: number
  isMuted: boolean

  // Data
  transcript: TranscriptMessage[]
  responses: QuestionResponse[]
  apiLog: ApiLogEntry[]

  // Config (dev controls only)
  config: CallConfig

  // Actions — call lifecycle
  initCall: (callId: string, patientId: string) => void
  setCallStatus: (status: CallStatus) => void
  incrementElapsed: () => void
  toggleMute: () => void
  resetCall: () => void

  // Actions — transcript
  addTranscriptMessage: (msg: TranscriptMessage) => void
  removeTranscriptMessage: (msgId: string) => void
  attachCapturedAnswer: (
    msgId: string,
    captured: { questionIndex: number; question: string; answer: string },
  ) => void

  // Actions — responses
  setResponses: (responses: QuestionResponse[]) => void
  updateResponse: (response: QuestionResponse) => void

  // Actions — api log
  logApi: (
    method: string,
    endpoint: string,
    status: number,
    body: unknown,
    latencyMs: number,
  ) => void
  clearApiLog: () => void

  // Actions — config
  setConfig: (config: Partial<CallConfig>) => void
}

const DEFAULT_CONFIG: CallConfig = {
  tone: "friendly",
  speed: 1.0,
  auto_greet: true,
  skip_answered: true,
}

export const useCallStore = create<CallStore>((set) => ({
  callId: null,
  patientId: null,
  callStatus: "idle",
  elapsed: 0,
  isMuted: false,
  transcript: [],
  responses: [],
  apiLog: [],
  config: DEFAULT_CONFIG,

  initCall: (callId, patientId) =>
    set({
      callId,
      patientId,
      callStatus: "idle",
      elapsed: 0,
      isMuted: false,
      transcript: [],
      responses: [],
      apiLog: [],
    }),

  setCallStatus: (callStatus) => set({ callStatus }),

  incrementElapsed: () => set((s) => ({ elapsed: s.elapsed + 1 })),

  toggleMute: () => set((s) => ({ isMuted: !s.isMuted })),

  resetCall: () =>
    set({
      callId: null,
      patientId: null,
      callStatus: "idle",
      elapsed: 0,
      isMuted: false,
      transcript: [],
      responses: [],
      apiLog: [],
      config: DEFAULT_CONFIG,
    }),

  addTranscriptMessage: (msg) =>
    set((s) => ({ transcript: [...s.transcript, msg] })),

  removeTranscriptMessage: (msgId) =>
    set((s) => ({ transcript: s.transcript.filter((m) => m.id !== msgId) })),

  attachCapturedAnswer: (msgId, captured) =>
    set((s) => ({
      transcript: s.transcript.map((m) =>
        m.id === msgId ? { ...m, capturedAnswer: captured } : m,
      ),
    })),

  setResponses: (responses) => set({ responses }),

  updateResponse: (response) =>
    set((s) => ({
      responses: s.responses.map((r) =>
        r.question_index === response.question_index ? response : r,
      ),
    })),

  logApi: (method, endpoint, status, body, latencyMs) =>
    set((s) => ({
      apiLog: [
        {
          id: crypto.randomUUID(),
          method,
          endpoint,
          status,
          body: JSON.stringify(body, null, 2),
          latencyMs,
          timestamp: Date.now(),
        },
        ...s.apiLog,
      ],
    })),

  clearApiLog: () => set({ apiLog: [] }),

  setConfig: (partial) =>
    set((s) => ({ config: { ...s.config, ...partial } })),
}))
