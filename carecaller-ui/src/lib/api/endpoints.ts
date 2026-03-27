const BASE = "/api"

export const ENDPOINTS = {
  patients: `${BASE}/patients`,
  patient: (id: string) => `${BASE}/patients/${id}`,
  questions: `${BASE}/questions`,
  call: {
    start: `${BASE}/call/start`,
    startVoice: `${BASE}/call/start-voice`,
    message: (callId: string) => `${BASE}/call/${callId}/message`,
    responses: (callId: string) => `${BASE}/call/${callId}/responses`,
    end: (callId: string) => `${BASE}/call/${callId}/end`,
    stream: (callId: string) => `${BASE}/call/${callId}/stream`,
  },
} as const
