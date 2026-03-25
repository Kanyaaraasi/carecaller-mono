// ── Call statuses & outcomes ──

export type CallStatus =
  | "idle"
  | "connecting"
  | "in-progress"
  | "completed"
  | "escalated"

export type CallOutcome =
  | "completed"
  | "incomplete"
  | "opted_out"
  | "scheduled"
  | "escalated"
  | "wrong_number"
  | "voicemail"

// ── Transcript ──

export interface TranscriptMessage {
  id: string
  role: "agent" | "user"
  text: string
  timestamp: number
  capturedAnswer?: {
    questionIndex: number
    question: string
    answer: string
  }
}

// ── Questions & Responses ──

export type QuestionStatus = "pending" | "asking" | "answered" | "skipped"

export interface Question {
  index: number
  text: string
}

export interface QuestionResponse {
  question_index: number
  question: string
  answer: string | null
  status: QuestionStatus
}

// ── Patient ──

export interface Patient {
  id: string
  name: string
  date_of_birth: string
  medication: string
  pharmacy: string
  phone: string
}

export interface GetPatientsResponse {
  patients: Patient[]
}

// ── Config ──

export type Tone = "friendly" | "neutral" | "formal"

export interface CallConfig {
  tone: Tone
  speed: number
  auto_greet: boolean
  skip_answered: boolean
}

// ── API request/response shapes ──

export interface StartCallRequest {
  patient_id: string
  config: CallConfig
}

export interface StartCallResponse {
  call_id: string
  status: CallStatus
  greeting_message: string
}

export interface SendMessageRequest {
  call_id: string
  message: string
  timestamp: number
}

export interface SendMessageResponse {
  agent_message: string
  captured_response: QuestionResponse | null
  current_question_index: number
  call_status: CallStatus
}

export interface GetResponsesResponse {
  call_id: string
  responses: QuestionResponse[]
  completeness: number
  transcript: TranscriptMessage[]
  outcome: CallOutcome | null
  duration_seconds: number | null
}

export interface EndCallRequest {
  call_id: string
  reason: string
}

export interface EndCallResponse {
  call_id: string
  outcome: CallOutcome
  duration_seconds: number
  responses: QuestionResponse[]
  completeness: number
  transcript: TranscriptMessage[]
}

export interface GetQuestionsResponse {
  questions: Question[]
}
