import { describe, it, expect } from "vitest"
import type {
  Patient,
  Question,
  QuestionResponse,
  TranscriptMessage,
  CallConfig,
  StartCallRequest,
  StartCallResponse,
  SendMessageResponse,
  GetResponsesResponse,
  EndCallResponse,
  ApiLogEntry,
} from "@/lib/api/types"

/**
 * These tests verify that the TypeScript types match the API contract.
 * They construct objects matching each interface and assert the shape.
 * If the types change and break the contract, these fail at compile time.
 */

describe("API Types Contract", () => {
  it("Patient matches expected shape", () => {
    const patient: Patient = {
      id: "pat_001",
      name: "Gabriella Shelton",
      date_of_birth: "1985-07-22",
      medication: "Tirzepatide",
      pharmacy: "CVS Pharmacy",
      phone: "+1-555-0101",
    }
    expect(patient.id).toBe("pat_001")
    expect(Object.keys(patient)).toHaveLength(6)
  })

  it("Question matches expected shape", () => {
    const question: Question = {
      index: 0,
      text: "How have you been feeling overall?",
    }
    expect(question.index).toBe(0)
    expect(Object.keys(question)).toHaveLength(2)
  })

  it("QuestionResponse allows null answer", () => {
    const pending: QuestionResponse = {
      question_index: 0,
      question: "Q1",
      answer: null,
      status: "pending",
    }
    const answered: QuestionResponse = {
      question_index: 0,
      question: "Q1",
      answer: "Pretty good",
      status: "answered",
    }
    expect(pending.answer).toBeNull()
    expect(answered.answer).toBe("Pretty good")
  })

  it("TranscriptMessage has optional capturedAnswer", () => {
    const withoutCapture: TranscriptMessage = {
      id: "msg_1",
      role: "user",
      text: "Hello",
      timestamp: 0,
    }
    const withCapture: TranscriptMessage = {
      id: "msg_2",
      role: "user",
      text: "233 pounds",
      timestamp: 5,
      capturedAnswer: {
        questionIndex: 1,
        question: "Current weight?",
        answer: "233",
      },
    }
    expect(withoutCapture.capturedAnswer).toBeUndefined()
    expect(withCapture.capturedAnswer?.answer).toBe("233")
  })

  it("CallConfig has all required fields", () => {
    const config: CallConfig = {
      tone: "friendly",
      speed: 1.0,
      auto_greet: true,
      skip_answered: true,
    }
    expect(config.tone).toBe("friendly")
    expect(Object.keys(config)).toHaveLength(4)
  })

  it("StartCallRequest accepts optional call_id", () => {
    const withId: StartCallRequest = {
      patient_id: "pat_001",
      call_id: "my_id",
      config: { tone: "friendly", speed: 1.0, auto_greet: true, skip_answered: true },
    }
    const withoutId: StartCallRequest = {
      patient_id: "pat_001",
      config: { tone: "friendly", speed: 1.0, auto_greet: true, skip_answered: true },
    }
    expect(withId.call_id).toBe("my_id")
    expect(withoutId.call_id).toBeUndefined()
  })

  it("StartCallResponse matches API contract", () => {
    const resp: StartCallResponse = {
      call_id: "call_001",
      status: "in-progress",
      greeting_message: "Hello!",
    }
    expect(resp.call_id).toBe("call_001")
    expect(Object.keys(resp)).toHaveLength(3)
  })

  it("SendMessageResponse has nullable captured_response", () => {
    const withCapture: SendMessageResponse = {
      agent_message: "Got it.",
      captured_response: { question_index: 0, question: "Q1", answer: "Yes", status: "answered" },
      current_question_index: 1,
      call_status: "in-progress",
    }
    const withoutCapture: SendMessageResponse = {
      agent_message: "Got it.",
      captured_response: null,
      current_question_index: 0,
      call_status: "in-progress",
    }
    expect(withCapture.captured_response?.answer).toBe("Yes")
    expect(withoutCapture.captured_response).toBeNull()
  })

  it("GetResponsesResponse has nullable outcome and duration", () => {
    const active: GetResponsesResponse = {
      call_id: "call_001",
      responses: [],
      completeness: 0.5,
      transcript: [],
      outcome: null,
      duration_seconds: null,
    }
    const ended: GetResponsesResponse = {
      call_id: "call_001",
      responses: [],
      completeness: 1.0,
      transcript: [],
      outcome: "completed",
      duration_seconds: 180,
    }
    expect(active.outcome).toBeNull()
    expect(ended.outcome).toBe("completed")
  })

  it("ApiLogEntry has all fields", () => {
    const entry: ApiLogEntry = {
      id: "log_1",
      method: "POST",
      endpoint: "/api/call/start",
      status: 200,
      body: "{}",
      latencyMs: 120,
      timestamp: Date.now(),
    }
    expect(entry.method).toBe("POST")
    expect(Object.keys(entry)).toHaveLength(7)
  })
})
