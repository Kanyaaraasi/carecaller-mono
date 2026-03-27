import { describe, it, expect } from "vitest"
import { ENDPOINTS } from "@/lib/api/endpoints"

describe("API Endpoints", () => {
  it("patients endpoint is /api/patients", () => {
    expect(ENDPOINTS.patients).toBe("/api/patients")
  })

  it("patient endpoint includes id", () => {
    expect(ENDPOINTS.patient("pat_001")).toBe("/api/patients/pat_001")
  })

  it("questions endpoint is /api/questions", () => {
    expect(ENDPOINTS.questions).toBe("/api/questions")
  })

  it("call start endpoint is /api/call/start", () => {
    expect(ENDPOINTS.call.start).toBe("/api/call/start")
  })

  it("call message endpoint includes callId", () => {
    expect(ENDPOINTS.call.message("abc123")).toBe("/api/call/abc123/message")
  })

  it("call responses endpoint includes callId", () => {
    expect(ENDPOINTS.call.responses("abc123")).toBe("/api/call/abc123/responses")
  })

  it("call end endpoint includes callId", () => {
    expect(ENDPOINTS.call.end("abc123")).toBe("/api/call/abc123/end")
  })

  it("call stream endpoint includes callId", () => {
    expect(ENDPOINTS.call.stream("abc123")).toBe("/api/call/abc123/stream")
  })
})
