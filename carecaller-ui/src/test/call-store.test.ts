import { describe, it, expect, beforeEach } from "vitest"
import { useCallStore } from "@/stores/call-store"

describe("CallStore", () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useCallStore.getState().resetCall()
  })

  describe("initCall", () => {
    it("sets callId and patientId", () => {
      useCallStore.getState().initCall("call_001", "pat_001")
      const state = useCallStore.getState()
      expect(state.callId).toBe("call_001")
      expect(state.patientId).toBe("pat_001")
    })

    it("resets all state on init", () => {
      const store = useCallStore.getState()
      store.setCallStatus("in-progress")
      store.addTranscriptMessage({
        id: "msg_1",
        role: "agent",
        text: "Hello",
        timestamp: 0,
      })

      store.initCall("call_002", "pat_002")
      const state = useCallStore.getState()
      expect(state.callStatus).toBe("idle")
      expect(state.transcript).toHaveLength(0)
      expect(state.elapsed).toBe(0)
    })
  })

  describe("transcript", () => {
    it("adds messages in order", () => {
      const store = useCallStore.getState()
      store.addTranscriptMessage({
        id: "msg_1",
        role: "agent",
        text: "Hello",
        timestamp: 0,
      })
      store.addTranscriptMessage({
        id: "msg_2",
        role: "user",
        text: "Hi",
        timestamp: 2,
      })

      const { transcript } = useCallStore.getState()
      expect(transcript).toHaveLength(2)
      expect(transcript[0].role).toBe("agent")
      expect(transcript[1].role).toBe("user")
    })

    it("removes message by id", () => {
      const store = useCallStore.getState()
      store.addTranscriptMessage({
        id: "msg_1",
        role: "user",
        text: "Hello",
        timestamp: 0,
      })
      store.addTranscriptMessage({
        id: "msg_2",
        role: "agent",
        text: "Hi",
        timestamp: 1,
      })

      store.removeTranscriptMessage("msg_1")
      const { transcript } = useCallStore.getState()
      expect(transcript).toHaveLength(1)
      expect(transcript[0].id).toBe("msg_2")
    })

    it("removeTranscriptMessage is no-op for unknown id", () => {
      const store = useCallStore.getState()
      store.addTranscriptMessage({
        id: "msg_1",
        role: "agent",
        text: "Hello",
        timestamp: 0,
      })

      store.removeTranscriptMessage("nonexistent")
      expect(useCallStore.getState().transcript).toHaveLength(1)
    })

    it("attaches captured answer to message", () => {
      const store = useCallStore.getState()
      store.addTranscriptMessage({
        id: "msg_1",
        role: "user",
        text: "233 pounds",
        timestamp: 5,
      })

      store.attachCapturedAnswer("msg_1", {
        questionIndex: 1,
        question: "Current weight?",
        answer: "233",
      })

      const msg = useCallStore.getState().transcript[0]
      expect(msg.capturedAnswer).toBeDefined()
      expect(msg.capturedAnswer?.answer).toBe("233")
    })
  })

  describe("responses", () => {
    it("sets responses array", () => {
      const store = useCallStore.getState()
      store.setResponses([
        { question_index: 0, question: "Q1", answer: null, status: "pending" },
        { question_index: 1, question: "Q2", answer: null, status: "pending" },
      ])

      expect(useCallStore.getState().responses).toHaveLength(2)
    })

    it("updates a single response by index", () => {
      const store = useCallStore.getState()
      store.setResponses([
        { question_index: 0, question: "Q1", answer: null, status: "pending" },
        { question_index: 1, question: "Q2", answer: null, status: "pending" },
      ])

      store.updateResponse({
        question_index: 0,
        question: "Q1",
        answer: "Pretty good",
        status: "answered",
      })

      const { responses } = useCallStore.getState()
      expect(responses[0].answer).toBe("Pretty good")
      expect(responses[0].status).toBe("answered")
      expect(responses[1].status).toBe("pending")
    })
  })

  describe("call status", () => {
    it("sets call status", () => {
      useCallStore.getState().setCallStatus("in-progress")
      expect(useCallStore.getState().callStatus).toBe("in-progress")
    })

    it("increments elapsed", () => {
      useCallStore.getState().incrementElapsed()
      useCallStore.getState().incrementElapsed()
      expect(useCallStore.getState().elapsed).toBe(2)
    })

    it("toggles mute", () => {
      expect(useCallStore.getState().isMuted).toBe(false)
      useCallStore.getState().toggleMute()
      expect(useCallStore.getState().isMuted).toBe(true)
      useCallStore.getState().toggleMute()
      expect(useCallStore.getState().isMuted).toBe(false)
    })
  })

  describe("api log", () => {
    it("logs API calls in reverse chronological order", () => {
      const store = useCallStore.getState()
      store.logApi("GET", "/api/patients", 200, {}, 50)
      store.logApi("POST", "/api/call/start", 200, {}, 120)

      const { apiLog } = useCallStore.getState()
      expect(apiLog).toHaveLength(2)
      expect(apiLog[0].endpoint).toBe("/api/call/start")
      expect(apiLog[1].endpoint).toBe("/api/patients")
    })

    it("clears api log", () => {
      const store = useCallStore.getState()
      store.logApi("GET", "/api/patients", 200, {}, 50)
      store.clearApiLog()
      expect(useCallStore.getState().apiLog).toHaveLength(0)
    })
  })

  describe("config", () => {
    it("partially updates config", () => {
      useCallStore.getState().setConfig({ tone: "formal" })
      const { config } = useCallStore.getState()
      expect(config.tone).toBe("formal")
      expect(config.speed).toBe(1.0) // unchanged
    })
  })

  describe("resetCall", () => {
    it("resets everything to initial state", () => {
      const store = useCallStore.getState()
      store.initCall("call_001", "pat_001")
      store.setCallStatus("in-progress")
      store.addTranscriptMessage({
        id: "m1",
        role: "agent",
        text: "hi",
        timestamp: 0,
      })
      store.setConfig({ tone: "formal" })

      store.resetCall()
      const state = useCallStore.getState()
      expect(state.callId).toBeNull()
      expect(state.callStatus).toBe("idle")
      expect(state.transcript).toHaveLength(0)
      expect(state.config.tone).toBe("friendly")
    })
  })
})
